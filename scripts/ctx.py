#!/usr/bin/env python3
"""ctx — the command line of the Grow PM context store (since v3.11.0).

  python3 ctx.py <command> [options] [--context PATH] [--store DIR] [--home DIR]

  status                        where the store is, records, card, edits waiting to be imported
  migrate [--apply]             split local-context.md into records (dry run unless --apply)
  compile                       import direct edits, then write both compiled copies and the card
  sync [--source S] [--reason R] [--resolve ID=file|record ...] [--accept-removals]
                                import direct edits to local-context.md into the records
  get ID [FIELD] [--json]       a record, or one `- **Field:** value`
  list [--type T] [--json]      records
  set ID FIELD VALUE            change or add a field line
  append ID --text T [--under "#### Heading"]   add a line (an identical line is not repeated)
  add TYPE TITLE [--parent ID] [--after ID] [--body-file F]   a new product, team, org, setting or custom record
  snapshot [--label L]          a snapshot of the store and both copies
  undo [--steps N]              back to the state before the N-th last change (N from 1); refused while
                                edits wait to be imported
  read --skill S [--product P]  the card plus what the skill's manifest entry names (reads only)
  invalidate ID --reason R      mark a record no longer current (it stays, with a status region)
  archive ID [--reason R]       move a record to the archive; restore ID brings it (or a trashed one) back
  verify [ID ...] [--stale]     mark records verified today
  validate                      records, ids, parents, card size, edits waiting
  card                          regenerate INDEX.md only
  repo list [--json]            the repositories (provider registrations) a product draws context blocks
                                from: kind, products, rank, access, version — reads local files, no network
  repo status [ID] [--json]     is each repository reachable (an MCP server answers the handshake within 3 s;
                                a folder is there) and its version on the source against the base — the only
                                repo command that touches the network: the handshake, then one read of the blocks
                                file for the version. It exits 0 also when a repository is unreachable
  provider adopt REPO [--apply] [--json]
                                a base for each block of REPO that is already in your context (dry run unless
                                --apply): the blocks the repository publishes at the version you hold are taken
                                as they are (an edit of yours counts as your edit); another version gets no base.
                                Writes the block state and the card's Repos line — never the records or the compiled copies
  provider plan [REPO] [--product P] [--all] [--json]
                                one table per repository: what each block is in your context against what the
                                repository publishes now (= ~ ✎ ⚠ + − ✂ ?), the questions and the records an apply
                                would rewrite. Without REPO: the repositories of the product P (matched as `read`
                                matches it), else all of them. --all also lists the blocks a repository skips.
                                Reads only — no lock, nothing written; an unreachable repository exits 5 (the
                                others still print). CTX_RESULT: with REPO the plan itself (rows, questions,
                                changes, errors …), without it {repos: [plan …], paused, questions, changes}.
                                Without REPO a paused repository is left out, with one line "призупинено: <id>"
  provider apply [REPO] [--product P] [--choose BLOCK=theirs|mine|both ...] [--add BLOCK ...] [--json]
                                one pass per repository: = ~ ✎ − ✂ are applied (your edits stay), ⚠ and ? wait
                                for --choose, + for --add (it goes to the record holding most of the repository's
                                blocks, else a new record); the snapshot, the records, the block state, one
                                journal line, the compile. Nothing moved: only the time of the check, "без змін".
                                Every repository is read first: one unreachable → exit 5, nothing written.
                                Exit 2 when an answer is awaited (the rest applied), 4 when only refused blocks
                                (a broken marker) are left. --choose / --add need REPO when several are in scope.
                                CTX_RESULT: the plan with applied, decisions, pending, ignored, written, snapshot

Every writing command takes the lock, refuses a store inside a provider's folder, imports direct
edits first, snapshots, writes, journals and compiles (the exception: `provider adopt --apply` imports
and compiles nothing — it writes the block state under `.state/blocks/`, and the card's Repos line). Files are read within a time budget
(GROW_PM_CTX_READ_TIMEOUT, default 30 s): a record that does not arrive (iCloud) or is missing
on disk stops the run before anything is written. The last stdout line is `CTX_RESULT {json}`;
a conflict prints `CTX_CONFLICT {json}` before it. Exit: 0 ok · 2 conflict · 3 bad input, no store,
unreadable record · 4 refused (managed region, provider boundary, busy lock, store exists) · 5 a repository is
unreachable, nothing written (provider commands). `provider apply`: 2 also means answers are awaited.
Semantics: references/context-protocol.md. Stdlib only.
"""
import argparse
import datetime
import json
import os
import sys
import urllib.parse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ctx_blocks as cb  # noqa: E402
import ctx_common as cc  # noqa: E402
import ctx_mcp as cm  # noqa: E402
import ctx_store as cs  # noqa: E402
import ctx_ops as co  # noqa: E402
import ctx_read as cr  # noqa: E402
import ctx_repos as crp  # noqa: E402
import ctx_schema as sc  # noqa: E402

HEADINGS = {"product": "### Product: %s", "team": "### Team: %s", "org": "## Organization: %s",
            "setting": "## %s", "custom": "## %s"}


class Usage(Exception):
    pass


WRITING = {"compile", "sync", "set", "append", "add", "snapshot", "undo", "card",
           "invalidate", "archive", "restore", "verify", "assign"}


def writes(a):
    """Does this run write to the store? Every command of WRITING does, and `provider apply`; `migrate` and `provider
    adopt` only with --apply."""
    if a.cmd in WRITING or (a.cmd == "provider" and getattr(a, "action", None) == "apply"):
        return True
    if a.cmd == "migrate" or (a.cmd == "provider" and getattr(a, "action", None) == "adopt"):
        return getattr(a, "apply", False)
    return False


class Parser(argparse.ArgumentParser):
    def error(self, message):
        raise Usage(message)


def now():
    return datetime.datetime.now().astimezone().isoformat(timespec="seconds")


class Ctx:
    def __init__(self, a):
        if a.store and writes(a):
            raise Usage("--store is for read commands only; writing commands use the context's own store")
        self.home = a.home or os.path.expanduser("~")
        found = cc.find_context(a.context, home=self.home)
        if not found:
            raise cs.StoreError("no such file: %s (--context)" % a.context if a.context else
                                "no local-context.md found (GROW_PM_CONTEXT_PATH, ~/.grow-pm)")
        self.context = os.path.realpath(found)
        self.text = co._read(self.context)
        self.store = cs.Store(a.store or co.store_root_for(self.text, self.home))
        self.copies = co.copies_for(self.context, self.text, self.home)

    def need_store(self):
        if not self.store.exists():
            raise cs.StoreError("no store at %s — `ctx migrate` shows the move" % self.store.root)

    def guard(self):
        regs = cc.find_registrations(cc.vault_entries(self.text),
                                     extra_dirs=[os.path.join(self.home, ".grow-pm", "providers")])
        hit = cc.boundary_hit(os.path.join(self.store.root, "records", "x.md"), regs)
        if hit:
            raise co.Refused("the store %s lies inside the provider %s's folder" % (self.store.root, hit.get("id")))
        for p in list(self.copies) + [self.store.root, self.store.records_dir, self.store.state_dir, self.store.card_path]:
            cs.check_target(p)
        co.purge_trash(self.home)

    def import_first(self):
        return co.apply_sync(self.store, co.plan_sync(self.store, self.copies), self.copies, self.home, None, "", now())


# ------------------------------------------------------------------ commands
def cmd_status(a, c):
    if not c.store.exists():
        if os.path.isdir(c.store.records_dir):
            print(co.half_migrated(c.store.root))
            return 3, {"command": "status", "store": None, "half_migrated": True}
        print("no store at %s — local-context.md is a single file; `ctx migrate` shows the move" % c.store.root)
        return 3, {"command": "status", "store": None}
    recs = c.store.load()
    plan = co.plan_sync(c.store, c.copies)
    pending = co.pending(plan)
    card = co._read(c.store.card_path).count("\n") if os.path.isfile(c.store.card_path) else 0
    tail = c.store.journal_entries()[-3:]
    stray = c.store.stray_files()
    stale = sc.stale_ids(recs, c.store.state(), now()[:10])
    invalid = [r["id"] for r in recs if cs.has_status_region(r["body"])]
    archived = len(c.store.archived())
    snaps = os.path.join(c.home, ".grow-pm", "snapshots")
    last = sorted(n for n in os.listdir(snaps) if co.SNAP_RE.match(n))[-1:] if os.path.isdir(snaps) else []
    print("store: %s · records %d · card %d lines" % (c.store.root, len(recs), card))
    print("freshness: %d stale · %d invalid · %d archived" % (len(stale), len(invalid), archived))
    print("last snapshot: %s" % (last[0] if last else "none"))
    print("to import: " + (", ".join("%s %d" % kv for kv in pending.items() if kv[1]) or "nothing — in sync"))
    for x in plan["conflicts"]:
        print("conflict: %s (%s)" % (x["id"], "; ".join(x["reasons"])))
    if plan["missing"]:
        print("missing on disk (not downloaded, not synced or deleted): %s — `ctx sync` says what to do"
              % ", ".join(i + ".md" for i in plan["missing"]))
    lonely = cs.unassigned_ids(recs)
    if lonely:
        print("custom without read_by: %s — ctx assign <id> all|<skills>" % ", ".join(lonely))
    for s in stray:
        print("stray file (ignored): %s" % s)
    for j in tail:
        print("journal: %s %s %s" % (j.get("ts", ""), j.get("op"), j.get("source", "")))
    return 0, {"command": "status", "store": c.store.root, "records": len(recs), "card_lines": card,
               "pending": pending, "conflicts": [x["id"] for x in plan["conflicts"]], "missing": plan["missing"],
               "stray": stray, "journal": tail, "stale": stale, "invalid": invalid, "archived": archived,
               "last_snapshot": last[0] if last else None, "unassigned": lonely}


def cmd_migrate(a, c):
    if a.apply:
        with co.lock(c.home):
            c.guard()
            rep = co.migrate(c.context, c.store.root, c.copies, c.home, True, now())
    else:
        rep = co.migrate(c.context, c.store.root, c.copies, c.home, False, now())
    print("store: %s" % rep["store"])
    print("round trip: %s" % ("identical" if rep["identical"] else "DIFFERENT — not migrating"))
    for r in rep["records"]:
        print("  %-48s %-10s %4d lines" % (r["id"], r["type"], r["lines"]))
    if rep["custom"]:
        print("not in the schema, kept as is: " + ", ".join(rep["custom"]))
    if rep["mirror_differs"]:
        print("the vault mirror differs from %s — the first compile rewrites it, after a snapshot" % c.context)
    print("migrated" if rep["applied"] else "dry run — nothing written; `ctx migrate --apply` moves it")
    return (0 if rep["identical"] else 3), dict(rep, command="migrate")


def _resolve(items):
    out = {}
    for it in items or []:
        rid, _, how = it.partition("=")
        if how not in ("file", "record") or not rid:
            raise Usage("--resolve takes ID=file or ID=record, not %r" % it)
        out[rid] = how
    return out


def cmd_sync(a, c, source=None):
    if not c.store.exists():
        if a.cmd == "sync":
            print("nothing to sync — no context store")
            return 0, {"command": "sync", "store": None}
        c.need_store()
    with co.lock(c.home):
        c.guard()
        plan = co.plan_sync(c.store, c.copies)
        res = co.apply_sync(c.store, plan, c.copies, c.home, source or getattr(a, "source", None),
                            getattr(a, "reason", None) or "", now(), resolve=_resolve(getattr(a, "resolve", None)),
                            accept_removals=getattr(a, "accept_removals", False))
    comp = res.get("compiled") or {}
    print("imported: %d changed, %d new, %d removed%s" % (len(res["changed"]), len(res["added"]), len(res["removed"]),
          " (recoverable: ctx undo)" if res["removed"] else ""))
    if res.get("moved"):
        print("order: the records follow the file (%d moved)" % len(res["moved"]))
    print("wrote: " + (", ".join(comp.get("written") or []) or "no copy needed a change"))
    return 0, dict(res, command=a.cmd)


def _record(c, rid):
    recs = {r["id"]: r for r in c.store.load()}
    if rid not in recs:
        raise cs.StoreError("no record %s — `ctx list` shows the ids" % rid)
    return recs[rid]


def _field_kind(rec):
    """The record's section of references/context-fields.yaml, or None."""
    if rec["type"] in ("profile", "product", "onboarding"):
        return rec["type"]
    return "judgment" if rec["type"] == "setting" and rec["title"].startswith("Judgment") else None


def _field_spec(rec, field):
    """The field's type from references/context-fields.yaml, or None (plain text)."""
    return (sc.load_fields().get(_field_kind(rec)) or {}).get(field)


def cmd_get(a, c):
    c.need_store()
    rec = _record(c, a.id)
    if a.section:
        name = a.section.lstrip("#").strip()
        part = cr._subsection(rec["body"], name)
        if part is None:
            raise cs.StoreError("no subsection %r in %s" % (name, a.id))
        sys.stdout.write(part)
        return 0, {"command": "get", "id": a.id, "section": name, "text": part if a.json else None}
    if a.field:
        spec = _field_spec(rec, a.field)
        raw = sc.raw_value(rec["body"], a.field, spec) if spec else cs.field_get(rec["body"], a.field)
        placeholder = cs.field_get(rec["body"], a.field) if raw is None and spec else None
        if placeholder is not None:            # the line is there with a placeholder such as _(not set)_
            print(placeholder)
            return 0, {"command": "get", "id": a.id, "field": a.field, "value": None, "not_set": True}
        if raw is None:
            raise cs.StoreError("no field %r outside managed regions in %s" % (a.field, a.id))
        print(raw)
        return 0, {"command": "get", "id": a.id, "field": a.field, "value": sc.parse_value(spec, raw) if spec else raw}
    sys.stdout.write(rec["body"] if rec["body"].endswith("\n") else rec["body"] + "\n")
    return 0, {"command": "get", "id": a.id, "body": rec["body"] if a.json else None}


def cmd_list(a, c):
    c.need_store()
    if a.archived:
        recs = [r for r in c.store.archived() if not a.type or r["type"] == a.type]
        for r in recs:
            print("%-48s %-10s archived %s  %s%s" % (r["id"], r["type"], r.get("archived") or "", r["title"],
                                                     " — " + r["archived_reason"] if r.get("archived_reason") else ""))
        return 0, {"command": "list", "archived": [{k: r.get(k) for k in ("id", "type", "title", "archived", "archived_reason")}
                                                   for r in recs]}
    if a.trash:
        items = [(p, r) for p, r in co.trash_entries(c.home) if not a.type or r["type"] == a.type]
        for p, r in items:
            print("%-48s %-10s trashed %s  %s" % (r["id"], r["type"], (r.get("trashed") or "")[:10], r["title"]))
        return 0, {"command": "list", "trash": [{"id": r["id"], "type": r["type"], "title": r["title"],
                                                 "trashed": r.get("trashed"), "file": p} for p, r in items]}
    recs = [r for r in c.store.load() if not a.type or r["type"] == a.type]
    for r in recs:
        print("%-48s %-10s %-10s %s" % (r["id"], r["type"], (r.get("modified") or "")[:10], r["title"]))
    return 0, {"command": "list", "records": [{k: r[k] for k in ("id", "type", "title", "parent", "modified")}
                                               for r in recs]}


def cmd_read(a, c):
    c.need_store()
    try:
        cr.manifest_for(cr.load_manifest(), a.skill)
    except KeyError:
        raise cs.StoreError("no manifest entry for %s — read local-context.md whole" % a.skill)
    try:
        repos = crp.load_repos(c.text, c.home)
    except Exception:  # noqa: BLE001 — the line that names a block's repository is not worth a read
        repos = []
    text, res = cr.read_view(c.store, c.copies, a.skill, product=a.product, today=now()[:10], repos=repos)
    sys.stdout.write(text)
    return 0, dict(res, command="read", skill=a.skill, text=text if a.json else None)


def _lifecycle(c, fn, *args):
    c.need_store()
    with co.lock(c.home):
        c.guard()
        return fn(c.store, c.copies, c.home, *args)


def cmd_invalidate(a, c):
    res = _lifecycle(c, co.invalidate, a.id, a.reason, now())
    print("invalidated %s · wrote %s" % (a.id, ", ".join(res["written"]) or "no copy"))
    return 0, dict(res, command="invalidate")


def cmd_archive(a, c):
    res = _lifecycle(c, co.archive, a.id, a.reason or "", now())
    print("archived %s · wrote %s (back: ctx restore %s)" % (a.id, ", ".join(res["written"]) or "no copy", a.id))
    return 0, dict(res, command="archive")


def cmd_restore(a, c):
    res = _lifecycle(c, co.restore_record, a.id, now())
    print("restored %s · wrote %s" % (a.id, ", ".join(res["written"]) or "no copy"))
    return 0, dict(res, command="restore")


def cmd_verify(a, c):
    if not a.ids and not a.stale:
        raise Usage("verify takes record ids or --stale")
    c.need_store()
    with co.lock(c.home):
        c.guard()
        c.import_first()
        done = co.verify(c.store, c.copies, c.home, a.ids, now(), stale=a.stale)
    print("verified today: %s" % (", ".join(done) or "nothing"))
    return 0, {"command": "verify", "ids": done}


def _write_one(c, op, rid, mutate, source, reason):
    c.need_store()
    with co.lock(c.home):
        c.guard()
        pre = c.import_first()
        rec = _record(c, rid)
        body = mutate(rec["body"])
        if body == rec["body"]:
            print("unchanged — %s already says that" % rid)
            return {"command": op, "id": rid, "changed": False, "imported": pre["changed"] + pre["added"]}
        t = now()
        snap = co.snapshot(c.store, c.copies, c.home, op)
        c.store.write(co.touch(dict(rec, body=body, source=source, modified=t), t))
        c.store.journal({"ts": t, "op": op, "ids": [rid], "source": source, "reason": reason or "", "snapshot": snap})
        comp = co.compile_store(c.store, c.copies, t, c.home, snap)
    print("%s: %s · wrote %s" % (op, rid, ", ".join(comp["written"]) or "no copy"))
    return {"command": op, "id": rid, "changed": True, "snapshot": snap, "imported": pre["changed"] + pre["added"],
            "written": comp["written"]}


def cmd_set(a, c):
    c.need_store()
    spec = _field_spec(_record(c, a.id), a.field)
    err = sc.check_value(spec, a.value) if spec else None
    if err:
        raise ValueError("%s: %s" % (a.field, err))
    return 0, _write_one(c, "set", a.id, lambda b: cs.field_set(b, a.field, a.value), a.source or "ctx-set", a.reason)


def _readers_value(text):
    """`all`, `none` (→ None) or skill names → the stored read_by value; unknown names → Usage."""
    v = text.strip().lower()
    if v == "none":
        return None
    if v == "all":
        return "all"
    names = sorted(cr.readers({"read_by": v}) or [])
    if not names:
        raise Usage("assign takes all, none or skill names separated by commas")
    unknown = [n for n in names if n not in (cr.load_manifest().get("skills") or {})]
    if unknown:
        raise Usage("unknown skill(s): %s — the names of skills/ folders" % ", ".join(unknown))
    return ", ".join(names)


def cmd_assign(a, c):
    """Who reads a custom or setting record in `ctx read` (read_by)."""
    value = _readers_value(a.readers)
    c.need_store()
    with co.lock(c.home):
        c.guard()
        pre = c.import_first()
        rec = _record(c, a.id)
        if rec["type"] not in ("custom", "setting"):
            raise Usage("read_by is for custom and setting records, not %s (%s)" % (rec["type"], a.id))
        if rec.get("read_by") == value:
            print("unchanged — %s already has read_by %s" % (a.id, value or "unset"))
            return 0, {"command": "assign", "id": a.id, "read_by": value, "changed": False, "snapshot": None}
        t = now()
        source = a.source or "ctx-assign"
        snap = co.snapshot(c.store, c.copies, c.home, "assign")
        c.store.write(dict(rec, read_by=value, source=source, modified=t))     # who reads it — not a content check
        c.store.journal({"ts": t, "op": "assign", "ids": [a.id], "source": source, "reason": a.reason or "",
                         "snapshot": snap})
        comp = co.compile_store(c.store, c.copies, t, c.home, snap)
    print("assign: %s read_by %s · wrote %s" % (a.id, value or "unset", ", ".join(comp["written"]) or "no copy"))
    return 0, {"command": "assign", "id": a.id, "read_by": value, "changed": True, "snapshot": snap,
               "imported": pre["changed"] + pre["added"]}


def cmd_append(a, c):
    return 0, _write_one(c, "append", a.id, lambda b: cs.append_line(b, a.text, under=a.under),
                         a.source or "ctx-append", a.reason)


def cmd_add(a, c):
    c.need_store()
    if a.type not in HEADINGS:
        raise Usage("add takes one of %s" % ", ".join(sorted(HEADINGS)))
    content = co._read(a.body_file) if a.body_file else ""
    heading = HEADINGS[a.type] % a.title
    text = heading + "\n\n" + (content.rstrip("\n") + "\n\n" if content.strip() else "")
    with co.lock(c.home):
        c.guard()
        c.import_first()
        recs = c.store.load()
        ids = [r["id"] for r in recs]
        if a.after:
            if a.after not in ids:
                raise cs.StoreError("no record %s" % a.after)
            after = a.after
        elif a.type in ("product", "team"):
            orgs = [r["id"] for r in recs if r["type"] == "org"]
            parent = a.parent or (orgs[0] if len(orgs) == 1 else None)
            if parent not in orgs:
                raise Usage("--parent names the organisation record (%s)" % ", ".join(orgs))
            same = [r["id"] for r in recs if r["type"] == a.type and r["parent"] == parent]
            kids = [r["id"] for r in recs if r["parent"] == parent]
            after = (same or kids or [parent])[-1]
        else:
            after = ids[-1] if ids else None
        t = now()
        snap = co.snapshot(c.store, c.copies, c.home, "add")
        title = heading.lstrip("#").strip()
        new = co._insert(c.store, [{"text": text, "type": a.type, "title": title, "after": after}],
                         a.source or "ctx-add", t)
        c.store.journal({"ts": t, "op": "add", "ids": new, "source": a.source or "ctx-add", "reason": a.reason or "",
                         "snapshot": snap})
        comp = co.compile_store(c.store, c.copies, t, c.home, snap)
    print("added %s after %s" % (new[0], after))
    return 0, {"command": "add", "id": new[0], "after": after, "snapshot": snap, "written": comp["written"]}


def cmd_snapshot(a, c):
    c.need_store()
    path = co.snapshot(c.store, c.copies, c.home, a.label or "manual")
    print(path)
    return 0, {"command": "snapshot", "snapshot": path}


def cmd_undo(a, c):
    if a.steps < 1:
        raise Usage("--steps takes a whole number from 1")
    c.need_store()
    with co.lock(c.home):
        c.guard()
        plan = co.plan_sync(c.store, c.copies)
        waiting = sum(co.pending(plan).values()) + len(plan["conflicts"]) + len(plan["missing"])
        if waiting:
            raise co.Refused("%d change(s) to local-context.md or the records are not imported yet and undo would "
                             "discard them — `ctx sync` first, then `ctx undo`" % waiting)
        marks = [e for e in c.store.journal_entries() if e.get("snapshot")]
        if len(marks) < a.steps:
            raise cs.StoreError("nothing to undo — the journal has %d change(s)" % len(marks))
        target = marks[-a.steps]["snapshot"]
        if not os.path.isdir(target):
            raise cs.StoreError("the snapshot %s is gone (rotated)" % target)
        jpath = os.path.join(c.store.state_dir, "journal.jsonl")
        journal = co._read(jpath)
        pre = co.snapshot(c.store, c.copies, c.home, "pre-undo")
        skipped = co.restore(target, c.store, c.copies)
        for p in skipped:
            print("skipped (not a current copy): %s" % p)
        with open(os.path.join(target, "manifest.json"), encoding="utf-8") as f:
            existed = json.load(f).get("store_existed")
        reverted = []
        if existed:
            cs.atomic_write(jpath, journal)
            t = now()
            c.store.journal({"ts": t, "op": "undo", "ids": [], "source": "undo", "reason": target, "snapshot": pre})
            # an import's snapshot holds the copies as they were on disk then — already edited; rebuild them
            # from the restored records so the edit is undone and nothing waits to be imported again. A compile's
            # own snapshot (a mirror created or rewritten) is the one case whose copies must stay as restored.
            # The same import of a record edited in its file (Obsidian) holds the edit in the records too: they
            # go back to the last compile's text first, or the rebuild would write the edit into the copies again.
            rebuilt = bool({m.get("op") for m in marks[-a.steps:]} - {"compile"})
            reverted = co.consistent_records(c.store, c.copies) if rebuilt else []
            if rebuilt:
                co.compile_store(c.store, c.copies, t, c.home, pre)
            print("restored the state before the %s — %s%s"
                  % ("last change" if a.steps == 1 else "%d last changes" % a.steps, target,
                     "; the copies were rebuilt from the records" if rebuilt else ""))
            if reverted:
                print("put back to the last compiled text (the edit made in the file is undone): %s" % ", ".join(reverted))
        else:
            co.forget_store(c.home)
            print("store removed — local-context.md is a single file again (the store is kept in %s)" % pre)
    return 0, {"command": "undo", "restored": target, "snapshot": pre, "store_removed": not existed, "skipped": skipped,
               "records_reverted": reverted}


def cmd_validate(a, c):
    c.need_store()
    errors, warnings = [], []
    try:
        recs = c.store.load()
    except cs.StoreError as e:
        errors.append(str(e))
        recs = []
    valid, odd = c.store.record_files()
    state = c.store.state()
    for r in recs:
        for field, spec in (sc.load_fields().get(_field_kind(r)) or {}).items():
            problem = sc.check_value(spec, sc.raw_value(r["body"], field, spec))
            if problem:
                warnings.append("%s: %s — %s%s" % (r["id"], field, problem, " (Step 0i asks once)" if field == "Role" else ""))
        if r.get("verified") is not None and sc._date(r.get("verified")) is None:
            warnings.append("%s: verified %r is not a date — the store's freshness date applies" % (r["id"], r.get("verified")))
        if r.get("ttl_days") is not None and not str(r.get("ttl_days")).strip().isdigit():
            warnings.append("%s: ttl_days %r is not a whole number — the type's default applies" % (r["id"], r.get("ttl_days")))
        if sc.is_stale(r, state, now()[:10]):
            warnings.append("stale: %s (verified %s, TTL %s d) — ctx verify %s" % (r["id"], sc.verified_of(r, state), sc.ttl_of(r), r["id"]))
    for name in valid:
        try:
            rid = cs.parse_record(co._read(os.path.join(c.store.records_dir, name)))["id"]
        except (OSError, ValueError, UnicodeDecodeError):
            continue
        if rid != name[:-3]:
            errors.append("%s: its frontmatter id %s differs from the file name — compile ignores it" % (name, rid))
    for name in odd:
        warnings.append("stray file, ignored by compile (a sync conflict copy?): %s" % name)
    ids = [r["id"] for r in recs]
    orders = [r["order"] for r in recs]
    if len(set(orders)) != len(orders):
        errors.append("two records share an order")
    for r in recs:
        if r["parent"] and r["parent"] not in ids:
            errors.append("%s: parent %s does not exist" % (r["id"], r["parent"]))
        if r["type"] == "product" and cs.field_get(r["body"], "Jira Project Key") is None:
            warnings.append("%s: no Jira Project Key (task-creator and requirements-creator need it)" % r["id"])
    skills = cr.load_manifest().get("skills") or {}
    for r in recs:
        unknown = sorted((cs.readers(r) or frozenset()) - {"all"} - set(skills))
        if unknown:
            warnings.append("%s: read_by names unknown skill(s): %s" % (r["id"], ", ".join(unknown)))
    lonely = cs.unassigned_ids(recs)
    if lonely:
        warnings.append("custom without read_by: %d (%s) — skills see only the card row; ctx assign <id> all|<skills>"
                        % (len(lonely), ", ".join(lonely)))
    if recs and not any(r["type"] == "profile" for r in recs):
        warnings.append("no User Profile record")
    if os.path.isfile(c.store.card_path) and co._read(c.store.card_path).count("\n") > cs.CARD_MAX:
        errors.append("INDEX.md is longer than %d lines" % cs.CARD_MAX)
    if recs or c.store.state().get("order"):
        plan = co.plan_sync(c.store, c.copies)
        for rid in plan["missing"]:
            errors.append("%s.md is missing on disk (not downloaded, not synced or deleted) — `ctx sync` says what to do" % rid)
        waiting = sum(co.pending(plan).values())
        if waiting:
            warnings.append("%d change(s) waiting — `ctx sync`" % waiting)
        for x in plan["conflicts"]:
            warnings.append("conflict: %s — `ctx sync` asks" % x["id"])
    for e in errors:
        print("error: " + e)
    for w in warnings:
        print("warning: " + w)
    print("valid" if not errors else "%d error(s)" % len(errors))
    return (3 if errors else 0), {"command": "validate", "errors": errors, "warnings": warnings}


def cmd_card(a, c):
    c.need_store()
    with co.lock(c.home):
        c.guard()
        recs = c.store.load()
        stale, archived = co.card_marks(c.store, recs, now()[:10])
        compiled = cs.compile_records(recs)
        card = cs.build_card(recs, compiled, now()[:10], stale=stale, archived=archived,
                             repos=co.card_repos(c.store, recs, compiled, c.home))
        cs.atomic_write(c.store.card_path, card)
    print("INDEX.md: %d lines" % card.count("\n"))
    return 0, {"command": "card", "card_lines": card.count("\n")}


def _table(rows):
    """Rows of texts as aligned columns; the first row is the header."""
    widths = [max(len(r[i]) for r in rows) for i in range(len(rows[0]))]
    return "\n".join("  ".join(cell.ljust(w) for cell, w in zip(r, widths)).rstrip() for r in rows)


NO_REPOS = ("no repositories registered — a registration is {vault}/{plugin folder}/_System/providers/<id>.yaml "
            "(references/context-provider-protocol.md §3b)")


def cmd_repo_list(a, c):
    skipped = []
    repos = crp.load_repos(c.text, c.home, skipped=skipped)
    if repos:
        rows = [("id", "kind", "products", "rank", "access", "blocks", "version", "checked")]
        for r in repos:      # blocks and checked come from the block state; none is kept yet
            rows.append((r["id"] + (" (paused)" if r["status"] == "paused" else ""), r["kind"] or "—",
                         ", ".join(r["products"]) or "all", str(r["rank"]), r["access"] or "—", "—",
                         r["source_version"] or "—", "—"))
        print(_table(rows))
    else:
        print(NO_REPOS)
    rows = []
    for r in repos:
        warning = crp.namespace_warning(r)
        if warning:
            print("warning: %s: %s" % (cb.clip(r["id"], cb.HEADER_CLIP), warning))
        rows.append(dict(r, namespace_warning=warning))
    for path, why in skipped:
        print("unreadable registration: %s (%s)" % (path, why))
    return 0, {"command": "repo", "action": "list", "repos": rows,
               "unreadable": [{"file": p, "reason": w} for p, w in skipped]}


def _public_url(url):
    """An endpoint as it may be shown: scheme, host, port and path — no credentials, no query, no fragment."""
    try:
        u = urllib.parse.urlsplit(url)
        return "%s://%s%s" % (u.scheme, u.netloc.rpartition("@")[2], u.path) if u.scheme and u.netloc else ""
    except ValueError:
        return ""


def _reach(r):
    """(reachable, reason) of one repository. An MCP repository answers the handshake within 3 s (the header its
    registration names, if any, comes from the environment); a folder or bundle is there when its core folder is."""
    ep = r["endpoint"]
    if r["kind"] == "mcp" or ep["url"]:
        if not ep["url"]:
            return False, "no endpoint url in the registration"
        hdrs = cm.headers_from_env(ep["headers_env"]) if ep["headers_env"] else {}
        client = cm.McpClient(ep["url"], headers=hdrs)
        if client.probe():
            return True, ""
        hint = "; %s is not set (or not 'Name: value')" % ep["headers_env"] if ep["headers_env"] and not hdrs else ""
        return False, client.last_error + hint
    if r["core_root"]:
        return (True, "") if os.path.isdir(r["core_root"]) else (False, "core folder not found")
    return False, "no endpoint and no core folder in the registration"


def cmd_repo_status(a, c):
    skipped = []
    repos = crp.load_repos(c.text, c.home, skipped=skipped)
    if a.id:
        repos = [r for r in repos if r["id"] == a.id]
        if not repos:
            raise Usage("no repository %r is registered — `ctx.py repo list`" % a.id)
    rows = []
    for r in repos:
        ok, why = _reach(r)
        # the version on the source is what its blocks carry now; the registration's own is the fallback when
        # the source cannot be read. The base is the version most of the blocks the store holds a base for are at.
        fetched = crp.fetch(r) if ok else None
        live = fetched["version"] if fetched else None
        warning = crp.namespace_warning(r, fetched["namespace"] if fetched else None)
        base, bad_state = None, None
        try:
            base = cb.base_version(cb.load_state(c.store, r["id"]))
        except cs.StoreError as e:                      # a status must not fail over a state file; it says so
            bad_state = str(e)
        rows.append({"id": r["id"], "kind": r["kind"], "status": r["status"], "url": _public_url(r["endpoint"]["url"]),
                     "reachable": ok, "reason": why, "source_version": live or r["source_version"], "base_version": base,
                     "namespace_warning": warning})
        if bad_state:
            rows[-1]["state_error"] = bad_state
    if rows:
        for row in rows:
            where = row["url"] or "—"
            print("%s  %s  %s" % (row["id"] + (" (paused)" if row["status"] == "paused" else ""), row["kind"] or "—", where))
            print("  reachable %s" % ("yes" if row["reachable"] else "no (%s)" % row["reason"]))
            print("  version on source: %s · base: %s" % (row["source_version"] or "—", row["base_version"] or "—"))
            if row.get("state_error"):
                print("  block state: %s" % row["state_error"])
            if row["namespace_warning"]:
                print("  warning: %s" % row["namespace_warning"])
    else:
        print(NO_REPOS)
    for path, why in skipped:
        print("unreadable registration: %s (%s)" % (path, why))
    return 0, {"command": "repo", "action": "status", "repos": rows,
               "unreadable": [{"file": p, "reason": w} for p, w in skipped]}


def cmd_repo(a, c):
    if a.action == "list":
        return cmd_repo_list(a, c)
    if a.action == "status":
        return cmd_repo_status(a, c)
    raise Usage("repo takes list or status")


def _repository(c, rid):
    """The registered repository named `rid`; an unknown one is a usage error (exit 3)."""
    repos = [r for r in crp.load_repos(c.text, c.home) if r["id"] == rid]
    if not repos:
        raise Usage("no repository %r is registered — `ctx.py repo list`" % rid)
    return repos[0]


def _refresh_card(c):
    """Bring the card's line about the repositories up to date after the state moved. The state is already written by
    then, so a card that cannot be read or written (an INDEX.md that has not arrived from iCloud, say) is one line for
    the caller to print after its report — "card not refreshed: <why>" — and never a lost report or another exit
    code. Returns that line, or None."""
    try:
        co.refresh_card_repos(c.store, c.home, now()[:10])
    except Exception as e:  # noqa: BLE001 — see above
        return "card not refreshed: %s" % cb.clip(e, cb.NOTE_CLIP)
    return None


def cmd_provider_adopt(a, c):
    c.need_store()
    repo = _repository(c, a.repo)
    fetched = crp.fetch(repo)
    if fetched["error"]:
        print("ctx: the repository %s is unreachable — %s" % (repo["id"], fetched["error"]))
        print("nothing written")
        return 5, {"command": "provider", "action": "adopt", "repo": repo["id"], "written": False, "error": fetched["error"]}
    plan = co.plan_sync(c.store, c.copies)
    pending = sum(co.pending(plan).values()) + len(plan["conflicts"]) + len(plan["missing"])
    if a.apply:
        with co.lock(c.home):
            c.guard()
            res = cb.adopt(c.store, c.copies, c.home, repo, fetched, now(), True)
            card_note = _refresh_card(c) if res["written"] else None
    else:
        res = cb.adopt(c.store, c.copies, c.home, repo, fetched, now(), False)
        card_note = None
    gets = [b for b, o in res["blocks"].items() if o in ("base", "edit")]
    print("adopt %s — source %s, %d block(s) of %s in your context" % (repo["id"], fetched["source"], len(res["blocks"]),
                                                                     cb.namespace_of(repo, fetched)))
    if res["blocks"]:
        print(_table([("block", "result", "why")] + [(b, o, res["why"][b]) for b, o in res["blocks"].items()]))
    if res["new"]:
        print("offered by the repository, not in your context (the plan shows +): " + ", ".join(res["new"]))
    for x in res["problems"]:
        print("problem: block %s in %s — %s (left out)" % (x["block"] or "?", x["host"], x["why"]))
    if pending:
        print("note: %d change(s) to local-context.md are not imported yet — `ctx sync` first, so adopt sees them" % pending)
    if res["written"]:
        print("adopted %d block(s) · snapshot %s (back: ctx undo)" % (len(gets), res["snapshot"]))
    elif a.apply:
        print("nothing to adopt — no base written")
    elif gets:
        print("dry run — nothing written; `ctx provider adopt %s --apply` sets the bases" % repo["id"])
    else:
        print("dry run — nothing written, and there is nothing to adopt")
    if card_note:
        print(card_note)
    return 0, dict(res, command="provider", action="adopt", pending=pending)


def _product_repos(c, repos, wanted):
    """The repositories that serve the product `wanted` names (picked among the product records the way `ctx read`
    picks it), and those that name no product (they serve all). An unknown or ambiguous product is a usage error."""
    records, _, _ = cr._live_view(c.store, c.copies, now())
    products = [r for r in records if r["type"] == "product"]
    prod, _ = cr._pick_product(products, wanted)
    if prod is None:
        raise Usage("no single product matches %r — products: %s" % (
            wanted, ", ".join(p["title"].split(":", 1)[-1].strip() for p in products) or "none"))
    names = {prod["id"].lower(), prod["title"].strip().lower(), prod["title"].split(":", 1)[-1].strip().lower()}
    return [r for r in repos if not r["products"] or names & {x.lower() for x in r["products"]}]


def _in_scope(c, a):
    """(repositories, ids of the paused ones) of a plan or an apply: the one named — paused or not — else those of the
    product --product names (and those serving every product), else all; without a name the paused are left out.
    Prints the line for an empty scope and one line "призупинено: <id>" per paused repository."""
    if a.repo:
        return [_repository(c, a.repo)], []
    repos = crp.load_repos(c.text, c.home)
    if a.product:
        repos = _product_repos(c, repos, a.product)
    paused = [r["id"] for r in repos if r["status"] == "paused"]
    repos = [r for r in repos if r["status"] != "paused"]
    if not repos and not paused:
        print(NO_REPOS if not a.product else "no repository serves the product %r" % a.product)
    for rid in paused:
        print("призупинено: %s" % cb.clip(rid, cb.HEADER_CLIP))
    return repos, paused


def cmd_provider_plan(a, c):
    c.need_store()
    repos, paused = _in_scope(c, a)
    plans, down = [], 0
    for k, repo in enumerate(repos):
        fetched = crp.fetch(repo, include_skipped=a.all)
        if k or paused:
            print()
        if fetched["error"]:
            down += 1
            why = cb.clip(fetched["error"], cb.NOTE_CLIP)
            print("%s · недоступний: %s" % (cb.clip(repo["id"], cb.HEADER_CLIP), why))
            plans.append({"repo": repo["id"], "error": why})
            continue
        plan = cb.plan(c.store, c.copies, repo, fetched, now(), all_=a.all)
        print(cb.render_plan(plan))
        plan["namespace_warning"] = crp.namespace_warning(repo, fetched["namespace"])
        if plan["namespace_warning"]:
            print("warning: %s" % plan["namespace_warning"])
        plans.append(plan)
    rc = 5 if down else 0
    if a.repo:
        return rc, dict(plans[0], command="provider", action="plan")
    return rc, {"command": "provider", "action": "plan", "repos": plans, "paused": paused,
                "questions": sum(p.get("questions", 0) for p in plans), "changes": sum(p.get("changes", 0) for p in plans)}


def _choices(items):
    """--choose BLOCK=theirs|mine|both … → {block: answer}; anything else is a usage error."""
    out = {}
    for it in items or []:
        bid, eq, how = it.partition("=")
        if not eq or not bid or how not in cb.CHOICES:
            raise Usage("--choose takes BLOCK=theirs|mine|both, not %r" % it)
        out[bid] = how
    return out


def _applied(res):
    """The data of one apply: the plan's (rows, versions …) and what the pass did."""
    out = dict(res["plan"])
    out.update((k, v) for k, v in res.items() if k != "plan")
    return out


def cmd_provider_apply(a, c):
    """One pass per repository: every repository is read first, and one that cannot be read stops the run before
    the lock (exit 5, nothing written); then, under the lock, the edits waiting are imported and each repository is
    applied (its own snapshot, journal line and compile). Exit 2 when an answer is still awaited (the rest applied),
    4 when a block was refused (a broken marker) and nothing else changed, else 0."""
    choose, add = _choices(a.choose), list(a.add or [])
    c.need_store()
    repos, paused = _in_scope(c, a)
    if (choose or add) and len(repos) > 1:
        raise Usage("--choose and --add answer one repository's plan — name it: ctx provider apply <repo> …")
    fetched = [(repo, crp.fetch(repo)) for repo in repos]
    down = [{"repo": repo["id"], "error": cb.clip(f["error"], cb.NOTE_CLIP)} for repo, f in fetched if f["error"]]
    if down:
        for x in down:
            print("%s · недоступний: %s" % (cb.clip(x["repo"], cb.HEADER_CLIP), x["error"]))
        print("нічого не записано")
        res = {"command": "provider", "action": "apply", "unreachable": down, "paused": paused, "written": []}
        if a.repo:
            res.update(repo=a.repo, error=down[0]["error"])
        return 5, res
    results, card_note = [], None
    if fetched:
        with co.lock(c.home):
            c.guard()
            c.import_first()
            for repo, f in fetched:
                results.append(cb.apply(c.store, c.copies, c.home, repo, f, choose, add, now()))
            card_note = _refresh_card(c)
    for k, res in enumerate(results):
        if k or paused:
            print()
        print(cb.render_apply(res))
    if card_note:
        print(card_note)
    if any(r["pending"] for r in results):
        rc = 2
    elif any(r["errors"] for r in results) and not any(r["changed"] for r in results):
        rc = 4
    else:
        rc = 0
    data = [_applied(r) for r in results]
    if a.repo:
        return rc, dict(data[0], command="provider", action="apply")
    return rc, {"command": "provider", "action": "apply", "repos": data, "paused": paused,
                "questions": sum(len(r["pending"]) for r in results), "changes": sum(len(r["written"]) for r in results)}


def cmd_provider(a, c):
    if a.action == "adopt":
        return cmd_provider_adopt(a, c)
    if a.action == "plan":
        return cmd_provider_plan(a, c)
    if a.action == "apply":
        return cmd_provider_apply(a, c)
    raise Usage("provider takes adopt, plan or apply")


# ---------------------------------------------------------------------- main
def build_parser():
    common = Parser(add_help=False)
    common.add_argument("--context")
    common.add_argument("--store")
    common.add_argument("--home")
    p = Parser(prog="ctx", description="The Grow PM context store (references/context-protocol.md).")
    sub = p.add_subparsers(dest="cmd", required=True, parser_class=Parser)
    sub.add_parser("status", parents=[common])
    sp = sub.add_parser("migrate", parents=[common]); sp.add_argument("--apply", action="store_true")
    sub.add_parser("compile", parents=[common])
    sp = sub.add_parser("sync", parents=[common])
    sp.add_argument("--source"); sp.add_argument("--reason")
    sp.add_argument("--resolve", action="append"); sp.add_argument("--accept-removals", action="store_true")
    sp = sub.add_parser("get", parents=[common]); sp.add_argument("id"); sp.add_argument("field", nargs="?")
    sp.add_argument("--section")
    sp.add_argument("--json", action="store_true")
    sp = sub.add_parser("list", parents=[common]); sp.add_argument("--type"); sp.add_argument("--json", action="store_true")
    g = sp.add_mutually_exclusive_group(); g.add_argument("--archived", action="store_true"); g.add_argument("--trash", action="store_true")
    sp = sub.add_parser("read", parents=[common]); sp.add_argument("--skill", required=True); sp.add_argument("--product")
    sp.add_argument("--json", action="store_true")
    sp = sub.add_parser("invalidate", parents=[common]); sp.add_argument("id"); sp.add_argument("--reason", required=True)
    sp = sub.add_parser("archive", parents=[common]); sp.add_argument("id"); sp.add_argument("--reason")
    sp = sub.add_parser("restore", parents=[common]); sp.add_argument("id")
    sp = sub.add_parser("verify", parents=[common]); sp.add_argument("ids", nargs="*"); sp.add_argument("--stale", action="store_true")
    sp = sub.add_parser("set", parents=[common]); sp.add_argument("id"); sp.add_argument("field"); sp.add_argument("value")
    sp.add_argument("--source"); sp.add_argument("--reason")
    sp = sub.add_parser("assign", parents=[common]); sp.add_argument("id"); sp.add_argument("readers")
    sp.add_argument("--source"); sp.add_argument("--reason")
    sp = sub.add_parser("append", parents=[common]); sp.add_argument("id"); sp.add_argument("--text", required=True)
    sp.add_argument("--under"); sp.add_argument("--source"); sp.add_argument("--reason")
    sp = sub.add_parser("add", parents=[common]); sp.add_argument("type"); sp.add_argument("title")
    sp.add_argument("--parent"); sp.add_argument("--after"); sp.add_argument("--body-file")
    sp.add_argument("--source"); sp.add_argument("--reason")
    sp = sub.add_parser("snapshot", parents=[common]); sp.add_argument("--label")
    sp = sub.add_parser("undo", parents=[common]); sp.add_argument("--steps", type=int, default=1)
    sub.add_parser("validate", parents=[common])
    sub.add_parser("card", parents=[common])
    rp = sub.add_parser("repo").add_subparsers(dest="action", required=True, parser_class=Parser)
    sp = rp.add_parser("list", parents=[common]); sp.add_argument("--json", action="store_true")
    sp = rp.add_parser("status", parents=[common]); sp.add_argument("id", nargs="?"); sp.add_argument("--json", action="store_true")
    pp = sub.add_parser("provider").add_subparsers(dest="action", required=True, parser_class=Parser)
    sp = pp.add_parser("adopt", parents=[common]); sp.add_argument("repo"); sp.add_argument("--apply", action="store_true")
    sp.add_argument("--json", action="store_true")
    sp = pp.add_parser("plan", parents=[common]); sp.add_argument("repo", nargs="?"); sp.add_argument("--product")
    sp.add_argument("--all", action="store_true"); sp.add_argument("--json", action="store_true")
    sp = pp.add_parser("apply", parents=[common]); sp.add_argument("repo", nargs="?"); sp.add_argument("--product")
    sp.add_argument("--choose", action="append"); sp.add_argument("--add", action="append")
    sp.add_argument("--json", action="store_true")
    return p


COMMANDS = {"status": cmd_status, "migrate": cmd_migrate, "compile": lambda a, c: cmd_sync(a, c, source="compile"),
            "sync": cmd_sync, "get": cmd_get, "list": cmd_list, "set": cmd_set, "append": cmd_append,
            "add": cmd_add, "snapshot": cmd_snapshot, "undo": cmd_undo, "validate": cmd_validate, "card": cmd_card,
            "read": cmd_read, "invalidate": cmd_invalidate, "archive": cmd_archive, "restore": cmd_restore,
            "verify": cmd_verify, "assign": cmd_assign, "repo": cmd_repo, "provider": cmd_provider}


def emit(result, conflict=None):
    if conflict is not None:
        print("CTX_CONFLICT " + json.dumps(conflict, ensure_ascii=False))
    print("CTX_RESULT " + json.dumps(result, ensure_ascii=False))


def main(argv=None):
    try:
        a = build_parser().parse_args(argv)
    except Usage as e:
        print("ctx: %s — `ctx.py --help`" % e)
        emit({"ok": False, "error": str(e)})
        return 3
    try:
        c = Ctx(a)
        with cs.guard_roots(co.allowed_roots(c.home, c.text)):
            rc, res = COMMANDS[a.cmd](a, c)
        emit(dict(res, ok=rc == 0))
        return rc
    except co.Conflict as e:
        print("ctx: %s" % e)
        emit({"ok": False, "command": a.cmd, "error": str(e)}, conflict=e.payload)
        return 2
    except (co.Refused, co.Busy, cs.RegionError, cs.PathRefused) as e:
        print("ctx: refused — %s" % e)
        emit({"ok": False, "command": a.cmd, "error": str(e)})
        return 4
    except Usage as e:
        print("ctx: %s" % e)
        emit({"ok": False, "command": a.cmd, "error": str(e)})
        return 3
    except (cs.StoreError, ValueError, OSError) as e:
        print("ctx: %s" % e)
        emit({"ok": False, "command": a.cmd, "error": str(e)})
        return 3


if __name__ == "__main__":
    sys.exit(main())
