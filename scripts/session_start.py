#!/usr/bin/env python3
"""Grow PM — SessionStart hook (since v2.6.0).

Finds the user's local-context.md wherever this session can see it and hands
the model a short digest as additionalContext, so Step 0a of
references/local-context-protocol.md becomes a lookup instead of a search.
Also exports GROW_PM_CONTEXT_PATH for later Bash calls via CLAUDE_ENV_FILE.

Design rules (see references/harness-map.md → hooks):
- Fail open. Any exception → exit 0, no output. A hook must never block a session.
- Header only. The digest carries paths, versions, names and flags — never
  URLs, ids, emails or tokens. Skills still parse the file themselves (0c–0j).
- Environment-agnostic. The user's home is a sandbox in hosted sessions; the
  context arrives through a connected folder mounted under $HOME/mnt/<name>/.
"""
import datetime
import glob
import json
import os
import re
import shlex
import sqlite3
import sys
import urllib.parse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:  # since v3.10.0 — shared helpers; absent → the v3.9.0 digest, still fail-open
    import ctx_common as cc
except Exception:
    cc = None

MAX_LINES = 25
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
        con = sqlite3.connect("file:%s?mode=ro" % urllib.parse.quote(p), uri=True, timeout=1)
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


def providers_info(text, extra_dirs=None, skipped=None):
    """[(id, label)], provider roots and the bundle facts — header-level only.
    Registrations that cannot be read land in `skipped` as (path, reason)."""
    if cc is None:
        return [], [], None
    entries = cc.vault_entries(text)
    regs = cc.find_registrations(entries, extra_dirs=extra_dirs, skipped=skipped)
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
        e["stale_after"] = int(r.get("stale_after_days") or 30) if str(r.get("stale_after_days") or "30").isdigit() else 30
    labels = []
    for pid in order:
        e = by_id[pid]
        mode = e.get("mode") or "live"
        access = e.get("access") or ("local" if e.get("index") else "open")
        bits, stale = [mode, access], False
        if e.get("synced"):
            bits.append("synced %s" % e["synced"])
            try:
                stale = (today - datetime.date.fromisoformat(e["synced"][:10])).days > e.get("stale_after", 30)
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


def parse(path, extra_dirs=None):
    """Header-level facts only."""
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
    try:
        facts["providers"], facts["provider_roots"], facts["bundle"] = providers_info(text, extra_dirs, facts["unreadable_registrations"])
    except Exception:
        facts["providers"], facts["provider_roots"], facts["bundle"] = [], [], None
    facts["cjm_section"] = bool(re.search(r"^## CJM Configuration\s*\n(?:.*\n){1,6}?.*(?:stages|funnel|template)", text, re.M | re.I))
    facts["terminology_section"] = bool(re.search(r"^### Terminology & Style", text, re.M))
    return facts


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
        bad = facts.get("unreadable_registrations") or []
        if bad:
            lines.append("  provider registration unreadable: %s" % "; ".join(
                "%s (%s)" % (os.path.basename(f), why) for f, why in bad[:3]))
        b = facts.get("bundle")
        if b:
            lines.append("  bundle: team=%s role=%s core=%s" % (b.get("team") or "?", b.get("role_profile") or "?", b.get("core_version") or "?"))
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
