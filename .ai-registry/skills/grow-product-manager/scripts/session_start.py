#!/usr/bin/env python3
"""Grow PM — SessionStart hook (since v2.6.0).

Finds the user's local-context.md wherever this session can see it and hands
the model a short digest as additionalContext, so Step 0a of
references/local-context-protocol.md becomes a lookup instead of a search.
Also exports GROW_PM_CONTEXT_PATH for later Bash calls via CLAUDE_ENV_FILE.

Design rules (see references/harness-map.md → hooks):
- Fail open. Any exception → exit 0, no output. A hook must never block a session.
- Header only. The digest carries paths, versions, names and flags — never
  URLs, ids, emails or tokens. The one exception is the `repos:` line (since v3.14.0): when a repository's
  sync failed it carries up to 80 characters of the reason — a server's or an exception's text, with the
  control characters stripped. Skills still parse the file themselves (0c–0j).
- Environment-agnostic. The user's home is a sandbox in hosted sessions; the
  context arrives through a connected folder mounted under $HOME/mnt/<name>/.
- No network, and two writes only: the store's summary beside a context that lies in a
  `.grow-pm` folder (`.ctx-summary.json`, since v3.13.1), and the two `export` lines
  (GROW_PM_CONTEXT_PATH, GROW_PM_PROVIDER_PATHS) appended to the file CLAUDE_ENV_FILE
  names, when the host sets it.
- The search index (since v3.16.0) is read from its `index.json` alone, within 0.2 s: the
  hook never opens its sqlite and never refreshes it.
"""
import datetime
import glob
import json
import os
import re
import shlex
import sqlite3
import sys
import threading
import time
import urllib.parse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:  # since v3.10.0 — shared helpers; absent → the v3.9.0 digest, still fail-open
    import ctx_common as cc
except Exception:
    cc = None

MAX_LINES = 25
REG_READ_S = 1.0     # seconds one provider registration may take to read (an iCloud download); ctx allows 3
REG_DEADLINE_S = 2.0  # …and all of them together (since v3.14): N evicted files never cost N seconds of the hook
INDEX_READ_S = 0.2    # seconds the search index's index.json may take to read (since v3.16.0)
ROLE_ENUM = {"pm", "head_of_product", "cpo", "product_designer", "product_analyst",
             "ux_researcher", "eng_lead", "business_owner", "other"}  # == references/role-profiles.md §2


def read_stdin():
    try:
        raw = sys.stdin.read()
        return json.loads(raw) if raw.strip() else {}
    except Exception:
        return {}


def candidates(cwd):
    home = os.path.expanduser("~")
    fixed = [
        os.path.join(home, ".grow-pm", "local-context.md"),
    ]
    globs = [
        os.path.join(home, "mnt", "*", "local-context.md"),
        os.path.join(home, "mnt", "*", ".grow-pm", "local-context.md"),
        os.path.join(home, "mnt", "*", "grow-pm", "local-context.md"),
        "/mnt/user-data/uploads/*/local-context.md",
        "/mnt/user-data/uploads/*/.grow-pm/local-context.md",
    ]
    tail = []
    for base in (cwd, os.environ.get("CLAUDE_PROJECT_DIR")):
        if base:
            tail.append(os.path.join(base, "local-context.md"))
            tail.append(os.path.join(base, ".grow-pm", "local-context.md"))
    out = list(fixed)
    for g in globs:
        out.extend(sorted(glob.glob(g)))
    out.extend(tail)
    seen, uniq = set(), []
    for p in out:
        if p not in seen:
            seen.add(p)
            uniq.append(p)
    return uniq


def plugin_version():
    try:
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        with open(os.path.join(root, ".claude-plugin", "plugin.json"), encoding="utf-8") as f:
            return json.load(f).get("version", "?")
    except Exception:
        return "?"


def _org_scope(text):
    """Text of the `## Organization` sections (products are declared there); without
    one, everything except `## Landscape`, whose per-product headings are settings."""
    parts = re.split(r"(?m)^(?=## (?!#))", text)
    org = [p for p in parts if p.startswith("## Organization")]
    return "".join(org) if org else "".join(p for p in parts if not p.startswith("## Landscape"))


def _uniq(xs):
    out = []
    for x in xs:
        if x not in out:
            out.append(x)
    return out


def _index_date(index_path):
    """meta.last_index of a vault/v1 index (context-provider-protocol.md §10), or None.
    The columns are key/value; k/v is read as a legacy spelling (v3.10.1)."""
    p = os.path.abspath(os.path.expanduser(index_path or ""))
    if not index_path or not os.path.isfile(p):
        return None
    try:
        uri = "file:%s?mode=ro" % urllib.parse.quote(p)
        con = sqlite3.connect(uri, uri=True, timeout=1)
        try:
            con.execute("PRAGMA schema_version").fetchone()
        except sqlite3.OperationalError as e:    # a WAL file alone, read as immutable (ctx_search.open_local, v4.0.1)
            con.close()
            if "unable to open" not in str(e).lower() or os.path.exists(p + "-wal"):
                raise
            con = sqlite3.connect(uri + "&immutable=1", uri=True, timeout=1)
        try:
            row = None
            for key, value in (("key", "value"), ("k", "v")):
                try:
                    row = con.execute("SELECT %s FROM meta WHERE %s='last_index'" % (value, key)).fetchone()
                    break
                except sqlite3.OperationalError:
                    continue
        finally:
            con.close()
        return datetime.datetime.fromisoformat(str(row[0]).replace("Z", "+00:00")) if row else None
    except Exception:
        return None


def _day(text):
    """The date a text starts with, or None."""
    try:
        return datetime.date.fromisoformat(str(text or "")[:10])
    except ValueError:
        return None


def _sync_daily(value):
    """Does a registration's raw `sync` value switch the daily sync on (since v3.14.0)? Exactly as `ctx_repos.normalise`
    reads it — a text that is "daily" in any case, trimmed; anything else, and no key, is off. Not imported from there: the
    hook stays light."""
    return isinstance(value, str) and value.strip().lower() == "daily"


def _sync_active(reg):
    """Does the raw registration `reg` take part in the daily sync (since v3.14.0)? `sync: daily` (`_sync_daily`) and not
    paused — as `ctx_synced.due` decides it from `ctx_repos.normalise`'s reading: the status is the trimmed text of the key
    (nothing, a list or a mapping is empty, which is active), and only exactly "paused" pauses (`Paused` does not). A
    paused repository keeps an old result in its state, which the repos line must not show."""
    status = reg.get("status")
    status = "" if status is None or isinstance(status, (list, dict)) else str(status).strip()
    return _sync_daily(reg.get("sync")) and status != "paused"


def providers_info(text, extra_dirs=None, skipped=None, checked=None, daily=None):
    """[(id, label)], provider roots and the bundle facts — header-level only.
    Registrations that cannot be read land in `skipped` as (path, reason). `checked` is {provider id: when the
    context store last checked it}: a day newer than the registration's `synced_at` is the day shown, and the
    one `stale` is counted from (since v3.13.0). Each registration is read within REG_READ_S seconds (since v3.13.1), and
    all of them within REG_DEADLINE_S (since v3.14): one that does not arrive (iCloud), or is not reached before that,
    lands in `skipped` as not available locally, and never holds the session start. `daily`,
    when a list, gets the ids of the registrations that say `sync: daily` and are not paused (`_sync_active`), in the
    providers' order (since v3.14.0)."""
    if cc is None:
        return [], [], None
    entries = cc.vault_entries(text)
    regs = cc.find_registrations(entries, extra_dirs=extra_dirs, skipped=skipped, timeout=REG_READ_S,
                                 deadline=time.monotonic() + REG_DEADLINE_S)
    by_id, order = {}, []
    for b in cc.vault_search_bullets(text):
        by_id[b["id"]] = {"mode": b["mode"], "access": b["access"], "index": b["index"]}; order.append(b["id"])
    today = datetime.date.today()
    for r in regs:
        e = by_id.setdefault(r["id"], {}); order += [] if r["id"] in order else [r["id"]]
        for k in ("mode", "access", "index"):
            if r.get(k):
                e[k] = str(r[k])
        e["synced"] = str(r.get("synced_at") or "")
        if daily is not None and _sync_active(r) and str(r["id"]) not in daily:
            daily.append(str(r["id"]))
        e["stale_after"] = int(r.get("stale_after_days") or 30) if str(r.get("stale_after_days") or "30").isdigit() else 30
    labels = []
    for pid in order:
        e = by_id[pid]
        mode = e.get("mode") or "live"
        access = e.get("access") or ("local" if e.get("index") else "open")
        bits, stale = [mode, access], False
        synced = e.get("synced")
        seen = _day((checked or {}).get(pid))
        if seen and (_day(synced) is None or seen > _day(synced)):
            synced = seen.isoformat()
        if synced:
            bits.append("synced %s" % synced)
            try:
                stale = (today - datetime.date.fromisoformat(synced[:10])).days > e.get("stale_after", 30)
            except ValueError:
                pass
        idx = _index_date(e.get("index"))
        if idx:
            bits.append("index %s" % idx.date().isoformat())
            now = datetime.datetime.now(idx.tzinfo) if idx.tzinfo else datetime.datetime.now()
            stale = stale or (now - idx).total_seconds() > 36 * 3600
        if stale:
            bits.append("stale")
        labels.append("%s (%s)" % (pid, ", ".join(bits)))
    roots = cc.provider_roots(regs)
    bundle = None
    for root in roots:
        for m in sorted(glob.glob(os.path.join(root, "*", "_System", "bundle-manifest.md"))) + \
                 sorted(glob.glob(os.path.join(root, "_System", "bundle-manifest.md"))):
            try:
                head = open(m, encoding="utf-8", errors="replace").read(2000)
            except OSError:
                continue
            f = {k: (re.search(r'^%s:\s*"?([^"\n]*?)"?\s*$' % k, head, re.M) or [None, ""])[1]
                 for k in ("team", "role_profile", "core_version")}
            bundle = f
            break
        if bundle:
            break
    return labels, roots, bundle


def index_info(home=None):
    """(sections, day) of the search index (since v3.16.0) from `<home>/.grow-pm/index/index.json` alone, read in a
    daemon thread within INDEX_READ_S; None when it is not there, not read in time, not an index state, or its count or
    day cannot be read. The index's sqlite is never opened here."""
    path = os.path.join(home or os.path.expanduser("~"), ".grow-pm", "index", "index.json")
    if not os.path.exists(path):
        return None
    box = {}

    def work():
        try:
            with open(path, encoding="utf-8") as f:
                box["data"] = json.load(f)
        except Exception:  # noqa: BLE001 — no line, never a failed digest
            pass

    t = threading.Thread(target=work, daemon=True)
    t.start()
    t.join(INDEX_READ_S)
    data = box.get("data") if not t.is_alive() else None
    if not isinstance(data, dict) or not str(data.get("schema") or "").startswith("search-index/"):
        return None
    sections, day = data.get("sections"), _day(data.get("updated"))
    if not isinstance(sections, int) or isinstance(sections, bool) or sections < 0 or day is None:
        return None
    return sections, day.isoformat()


def _store_summary(path, budget_s=2.0, dates_s=0.5):
    """The context store's summary (since v3.11.0), counted within a time budget so an iCloud download can never hold
    the session start; any failure → None (no line). Since v3.13.1 one helper does it for the digest and for `ctx`
    (`ctx_ops.summary_in_time`): the facts within `budget_s`, then the days the repositories were last checked
    (`checked`, since v3.13.0) and the results of the daily sync (`sync`, since v3.14.0: the repos line) within `dates_s`
    more — a block state that does not arrive (an iCloud-evicted `.state/blocks/<repo>.json`) costs the days and the
    results, never the context line; the providers line falls back to `synced_at`, the repos line is left out, and the
    cache keeps the days and the results saved before. A summary counted in time is saved beside the context; a count that
    misses the budget — a cold start: iCloud, an antivirus scan — gives the one saved last instead (at most 7 days old,
    with `cached_at`; its days are the saved ones). A count that comes back empty in time (no store, an error) is the
    answer: no line, the cache is not used."""
    try:
        import ctx_ops
        return ctx_ops.summary_in_time(path, cached=True, facts_s=budget_s, dates_s=dates_s)
    except Exception:
        return None


def parse(path, extra_dirs=None, home=None):
    """Header-level facts only. `home` (since v3.16.0) is where the search index is looked for (`~` by default)."""
    with open(path, encoding="utf-8", errors="replace") as f:
        text = f.read()
    # since v3.10.0: provider blocks (managed regions) repeat `### Team:` / `### Product:`
    # headings — count the user's own sections only
    plain = cc.strip_managed_regions(text) if cc else text
    facts = {}
    m = re.search(r"^> Configurator version:\s*(\S+)", text, re.M)
    facts["configurator_version"] = m.group(1) if m else "unknown"
    m = re.search(r"^> Generated:.*?Updated:\s*([0-9]{4}-[0-9]{2}-[0-9]{2})", text, re.M)
    facts["updated"] = m.group(1) if m else "unknown"
    m = re.search(r"^- \*\*Language:\*\*\s*([a-z]{2})\b", text, re.M)
    facts["language"] = m.group(1) if m else "unknown"
    m = re.search(r"^- \*\*Mode:\*\*\s*(basic|extended)\b", text, re.M)
    facts["onboarding_mode"] = m.group(1) if m else "unknown"
    # Role layer (v3.5.0): print only what the file says — the enum value, "legacy"
    # for a free-text role written before v3.5.0, or "absent". Never the free-text
    # label (it may carry an org name); Step 0i derives level_home when missing.
    m = re.search(r"^- \*\*Role:\*\*[ \t]*([^\n]*)$", text, re.M)
    raw = re.sub(r"<!--.*?-->", "", m.group(1)).strip() if m else ""
    facts["role"] = raw if raw in ROLE_ENUM else ("legacy" if raw else "absent")
    m = re.search(r"^- \*\*Level home:\*\*\s*(L[1-4])\b", text, re.M)
    facts["level_home"] = m.group(1) if m else "derived at Step 0i"
    facts["products"] = _uniq(re.findall(r"^### Product:\s*(.+?)\s*$", _org_scope(plain), re.M))
    facts["teams"] = _uniq(re.findall(r"^### Team:\s*(.+?)\s*$", plain, re.M))
    # deferred steps: indented bullets right after the marker line
    deferred = []
    m = re.search(r"^- \*\*Deferred steps:\*\*\s*\n((?:\s+- .+\n?)*)", text, re.M)
    if m:
        deferred = re.findall(r"^\s+- (\S+)", m.group(1), re.M)
    if not deferred:  # the onboarding skeleton may write an inline comma list
        m = re.search(r"^- \*\*Deferred steps:\*\*[ \t]*([^\n\[]+)$", text, re.M)
        if m:
            deferred = [s.strip() for s in m.group(1).split(",") if s.strip()]
    facts["deferred_steps"] = [s for s in deferred if not re.fullmatch(r"_?none_?|n/a|—|-", s, re.I)]
    vault = re.search(r"^## Obsidian Vaults", text, re.M) and re.search(r"^\s*-\s*path:\s*\S+", text, re.M)
    facts["vault_section"] = bool(vault) or bool(cc and cc.vault_entries(text))  # table format too (v3.10.0)
    facts["unreadable_registrations"] = []
    facts["context_store"] = _store_summary(path)   # first: the providers line takes the days of the last checks from it
    facts["daily_sync"] = []                        # the registrations with `sync: daily`: the repos line shows only those
    try:
        facts["providers"], facts["provider_roots"], facts["bundle"] = providers_info(
            text, extra_dirs, facts["unreadable_registrations"], (facts["context_store"] or {}).get("checked"),
            daily=facts["daily_sync"])
    except Exception:
        facts["providers"], facts["provider_roots"], facts["bundle"] = [], [], None
    try:
        facts["index"] = index_info(home)
    except Exception:  # noqa: BLE001
        facts["index"] = None
    facts["cjm_section"] = bool(re.search(r"^## CJM Configuration\s*\n(?:.*\n){1,6}?.*(?:stages|funnel|template)", text, re.M | re.I))
    facts["terminology_section"] = bool(re.search(r"^### Terminology & Style", text, re.M))
    return facts


REPOS_SHOWN = 3      # repositories the repos line names; the rest is "+N"
REASON_CLIP = 80     # characters of a reason (a broken source, an error) the repos line carries


def _count(value):
    """A count the state keeps (updated, added, removed): a whole number of 0 or more; anything else is 0."""
    return value if isinstance(value, int) and not isinstance(value, bool) and value > 0 else 0


def _items(value):
    """How many blocks a list of the state names (kept_yours, awaiting, held, held_behind); anything but a list is 0."""
    return len(value) if isinstance(value, list) else 0


def _sync_part(rid, result, checked):
    """What the repos line says of one repository — `<id> · …` — from its last `sync_result` (the block state's, or the
    summary's) and the day it was last checked (`checked`, an ISO text or None); None when there is nothing to say: no result,
    one that is not an object, or an outcome of a newer plugin than this hook. The formats are spec §8's, and every text
    that came from a state or a server goes through `clip` (a line is one line). A pass that held blocks because the
    source lags behind your bases (`held_behind`, a non-empty list; a result written before the key existed has none)
    says `⚠ source behind — nothing taken` right after its synced date."""
    if not isinstance(result, dict) or cc is None:
        return None
    outcome = result.get("outcome")
    shown = cc.clip(rid, 64)
    attempt = _day(result.get("at"))             # the pass's own day
    since = _day(checked)                        # the last successful check
    day = attempt or since
    synced = "synced %s" % day.isoformat() if day else "synced"
    awaits = _items(result.get("awaiting"))
    if outcome in ("changed", "no-changes"):
        bits = [synced]
        if _items(result.get("held_behind")):     # a lagging source held what it offered: never a silent «no changes»
            bits.append("⚠ source behind — nothing taken")
        changed = _count(result.get("updated")) + _count(result.get("added")) + _count(result.get("removed"))
        kept = _items(result.get("kept_yours"))
        if outcome == "no-changes":
            bits.append("no changes")
        if changed:
            bits.append("%d updated" % changed)
        if kept:
            bits.append("%d conflict%s kept yours" % (kept, "" if kept == 1 else "s"))
        report = result.get("report")
        if isinstance(report, str) and cc.clip(report, 200):
            bits.append("report %s" % cc.clip(report, 200))
    elif outcome == "held":
        held = _items(result.get("held"))
        bits = ["⚠ %sremovals held — ctx provider plan %s" % ("%d " % held if held else "", shown)]
    elif outcome == "unreachable":
        bits = ["unreachable since %s (VPN?)" % since.isoformat() if since else "unreachable (VPN?)"]
    elif outcome == "timeout":
        bits = ["sync timed out %s" % attempt.isoformat() if attempt else "sync timed out"]
    elif outcome in ("broken", "error"):
        reason = cc.clip(result.get("reason") if isinstance(result.get("reason"), str) else "", REASON_CLIP)
        head = "⚠ source broken" if outcome == "broken" else "⚠ sync error"
        bits = [head + (" — %s" % reason if reason else "")]
    elif outcome == "import-conflict":
        bits = ["⚠ edits to import first — ctx sync"]
    else:
        return None
    if awaits:
        bits.append("%d block(s) awaits a decision" % awaits)
    return " · ".join([shown] + bits)


def _repos_line(daily, sync, checked):
    """`  repos: <part>; <part>; <part>; +N` (since v3.14.0): the last result of the daily sync of each repository the
    registrations switch on (`daily`: their ids in order; a repository whose sync was switched off, or is paused, keeps an
    old result in its state, which is not shown), at most REPOS_SHOWN parts and the count of the rest. None when no repository has
    anything to say. `sync` and `checked` are the summary's ({id: sync_result}, {id: when it was last checked})."""
    sync, checked = sync if isinstance(sync, dict) else {}, checked if isinstance(checked, dict) else {}
    parts = []
    for rid in daily or []:
        try:
            part = _sync_part(rid, sync.get(rid), checked.get(rid))
        except Exception:  # noqa: BLE001 — one state of the wrong kind is that repository's part only
            part = None
        if part:
            parts.append(part)
    if not parts:
        return None
    shown = parts[:REPOS_SHOWN] + (["+%d" % (len(parts) - REPOS_SHOWN)] if len(parts) > REPOS_SHOWN else [])
    return "  repos: " + "; ".join(shown)


def digest(path, facts, searched, version):
    lines = [
        "GROW_PM_SESSION (SessionStart hook, plugin v%s)" % version,
        "local-context.md: FOUND at %s" % path,
        "  configurator version: %s | updated: %s | onboarding mode: %s | user.language: %s"
        % (facts["configurator_version"], facts["updated"], facts["onboarding_mode"], facts["language"]),
    ]
    lines.append("  user.role: %s | level_home: %s" % (facts["role"], facts["level_home"]))
    if facts["products"]:
        lines.append("  products (%d): %s" % (len(facts["products"]), "; ".join(facts["products"][:8])))
    else:
        lines.append("  products: none declared")
    if facts["teams"]:
        lines.append("  teams: %s" % "; ".join(facts["teams"][:6]))
    flags = []
    flags.append("vault: configured" if facts["vault_section"] else "vault: not configured (L0)")
    flags.append("cjm: configured" if facts["cjm_section"] else "cjm: not configured")
    flags.append("team language: configured" if facts["terminology_section"] else "team language: not configured")
    lines.append("  " + " | ".join(flags))
    if facts["deferred_steps"]:
        lines.append("  deferred onboarding steps: %s" % ", ".join(facts["deferred_steps"][:10]))
    if cc is not None:
        prov = facts.get("providers") or []
        lines.append("  providers: %s" % (", ".join(prov[:6]) if prov else "none declared"))
        if facts.get("index"):                      # since v3.16.0: the search index, from its index.json
            lines.append("  index: секцій %d · оновлено %s" % facts["index"])
        bad = facts.get("unreadable_registrations") or []
        if bad:
            lines.append("  provider registration unreadable: %s" % "; ".join(
                "%s (%s)" % (os.path.basename(f), why) for f, why in bad[:3]))
        b = facts.get("bundle")
        if b:
            lines.append("  bundle: team=%s role=%s core=%s" % (b.get("team") or "?", b.get("role_profile") or "?", b.get("core_version") or "?"))
    s = facts.get("context_store")
    if s and s.get("unavailable"):
        lines.append("  context: store at %s unavailable — vault not mounted?" % s["unavailable"])
    elif s:
        if s["conflicts"]:
            tail = "%d conflict%s (ctx sync)" % (s["conflicts"], "" if s["conflicts"] == 1 else "s")
        elif s["pending"]:
            tail = "%d edit%s to import" % (s["pending"], "" if s["pending"] == 1 else "s")
        else:
            tail = "in sync"
        if s.get("stale"):
            tail += " · %d stale" % s["stale"]
        if s.get("unassigned"):
            tail += " · %d custom unassigned" % s["unassigned"]
        if s.get("cached_at"):                     # since v3.13.1: the summary saved last, on a cold start
            tail += " · cached %s" % s["cached_at"][:16].replace("T", " ")
        lines.append("  context: records %d · card %d lines · %s" % (s["records"], s["card_lines"], tail))
        try:                                       # since v3.14.0: the daily sync's result per repository — a state never fails the digest
            repos = _repos_line(facts.get("daily_sync"), s.get("sync"), s.get("checked"))
        except Exception:  # noqa: BLE001
            repos = None
        if repos:
            lines.append(repos)
    if s and not s.get("unavailable"):
        lines.append(
            'Skills: run python3 "<plugin root>/scripts/ctx.py" provider sync --if-due (repeat any line it prints that starts '
            "«Ядро оновило» at the end of your answer), then "
            "take this path for Step 0a of references/local-context-protocol.md and skip the "
            "location search. A context store exists: where a skill says to read local-context.md (Step 0c), "
            'run python3 "<plugin root>/scripts/ctx.py" read --skill <your name> --product "<the product the '
            'request names>" (no --product when it names none) and use its output instead of reading '
            "local-context.md; read the file whole only if that exits 3 (references/context-protocol.md). "
            "Env GROW_PM_CONTEXT_PATH is set for Bash."
        )
    else:
        lines.append(
            "Skills: take this path for Step 0a of references/local-context-protocol.md and skip the "
            "location search; still parse the file for 0c–0j (product selection, required fields, vault "
            "level, role, judgment contract). Env GROW_PM_CONTEXT_PATH is set for Bash."
        )
    return "\n".join(lines[:MAX_LINES])


def not_found(searched, version):
    shown = [p for p in searched if "*" not in p][:6]
    return "\n".join([
        "GROW_PM_SESSION (SessionStart hook, plugin v%s)" % version,
        "local-context.md: NOT VISIBLE from this environment (searched %d locations, e.g. %s)."
        % (len(searched), ", ".join(shown)),
        "Skills follow references/local-context-protocol.md Step 0 unchanged (device/file tools, or "
        "the user connects the ~/.grow-pm folder). Do not start onboarding on this signal alone.",
    ])


def export_env(path, provider_paths=()):
    env_file = os.environ.get("CLAUDE_ENV_FILE")
    if not env_file:
        return
    try:
        with open(env_file, "a", encoding="utf-8") as f:
            # shlex, not JSON: bash keeps \uXXXX escapes literally, and folder names may be non-ASCII
            f.write("export GROW_PM_CONTEXT_PATH=%s\n" % shlex.quote(path))
            f.write("export GROW_PM_PROVIDER_PATHS=%s\n" % shlex.quote(os.pathsep.join(provider_paths)))
    except Exception:
        pass


def main():
    data = read_stdin()
    cwd = data.get("cwd") or os.getcwd()
    version = plugin_version()
    searched = candidates(cwd)
    existing = [p for p in searched if os.path.isfile(p)]
    # Rank: the canonical store (~/.grow-pm) first, then any path with a grow-pm
    # segment (a connected copy of the store), then plain copies — a workspace
    # folder may hold a stale export next to design docs.
    def rank(p):
        low = p.lower()
        if low.startswith(os.path.expanduser("~").lower() + os.sep + ".grow-pm"): return 0
        if "/.grow-pm/" in low or "/grow-pm/" in low: return 1
        return 2
    existing.sort(key=rank)
    found = existing[0] if existing else None
    if found:
        facts = {}
        try:
            facts = parse(found)
            text = digest(found, facts, searched, version)
            if len(existing) > 1:
                text += "\nOther copies seen (not used; check they are not stale): " + "; ".join(existing[1:4])
        except Exception:
            text = "GROW_PM_SESSION (plugin v%s)\nlocal-context.md: FOUND at %s (digest unavailable — parse error; skills read it themselves)." % (version, found)
        export_env(found, facts.get("provider_roots") or [])
    else:
        text = not_found(searched, version)
    print(json.dumps({"hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": text}}))


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass
    sys.exit(0)
