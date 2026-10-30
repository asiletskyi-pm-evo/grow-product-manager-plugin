#!/usr/bin/env python3
"""tools_scan.py — the tools registry of knowledge-library (references/tool-registry.md).

  scan     the names of what is installed on this machine, one JSON line each
  merge    seed + scan + observed rows -> registry.json, tools.md, scans/<date>.jsonl
  suggest  at most one record a skill may offer at its step
  decline  the user's «ні» to a suggestion in one skill (--undo takes it back)
  add      a record by hand, or a team's record taken over (--from-team)
  set      the user's own fields of a record
  team     the lists the user's cores publish (`tools_file`), read-only
  export   the records the user marked shared, one file for a core's owner

Names only: from a host's configuration the scan takes the keys of its MCP server map and the section
headers of a TOML file — never a value under them (command, args, env, headers, url). Every command
ends with one `TOOLS_RESULT {json}` line. Stdlib only (Python 3.9). Exit 0; 2 for wrong arguments or
an unknown record; 1 when the store cannot be written.
"""
import argparse, datetime, glob, json, os, re, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import ctx_common as cc  # noqa: E402
import ctx_never as cn  # noqa: E402

SEED = os.path.join(ROOT, "references", "tools-seed.yaml")
SCHEMA = "tools-registry/1"
SELF = "grow-product-manager"
KINDS = ("plugin", "skill", "mcp", "app", "cli", "site", "portal", "course")
ACCESS = ("free", "paid", "corporate", "unknown")
VERDICTS = ("tried", "recommended", "deprecated")
PUBLISHES = ("board", "page", "document", "deck", "dashboard", "design")
STATES = ("connected", "needs-auth", "installed", "not-installed", "not-seen")
OBSERVED = ("connected", "needs-auth", "installed")          # what a row can say; the rest the merge derives
RANK = {s: i for i, s in enumerate(STATES)}
SEED_FIELDS = ("name", "kind", "job", "skills", "contours", "access", "connect", "publishes")
USER_FIELDS = ("verdict", "shared", "recommended_by", "connect", "job", "access", "skills", "contours",
               "publishes", "checked", "notes")
LIST_FIELDS = ("skills", "contours")
EXPORT_FIELDS = ("name", "kind", "job", "skills", "contours", "access", "connect", "verdict", "recommended_by",
                 "checked", "publishes")
MAX_NAME, MAX_TEXT, MAX_DESC = 120, 300, 200


def today():
    return datetime.date.today().isoformat()


def norm(s):
    return re.sub(r"[^a-z0-9]", "", str(s or "").lower())


def clean(s, limit=MAX_TEXT):
    s = re.sub(r"[\x00-\x1f\x7f]+", " ", str(s or "")).strip()
    return s[:limit]


def result(**kw):
    print("TOOLS_RESULT " + json.dumps(kw, ensure_ascii=False, sort_keys=True))


# ------------------------------------------------------------------ host files (names only)
def _json_keys(path, *ways):
    """The keys of the maps found at `ways` (tuples of keys; '*' walks every value) in a JSON file — never a value."""
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError, UnicodeDecodeError):
        return None
    out = []
    for way in ways:
        nodes = [data]
        for k in way:
            nxt = []
            for n in nodes:
                if not isinstance(n, dict):
                    continue
                nxt.extend(n.values() if k == "*" else [n.get(k)])
            nodes = nxt
        for n in nodes:
            if isinstance(n, dict):
                out.extend(str(k) for k in n.keys())
    return out


_TOML_HEADER = re.compile(r"^\s*\[\s*([^\[\]]+?)\s*\]\s*(?:#.*)?$")


def _toml_tables(path, prefix):
    """The names right after `prefix.` in a TOML file's table headers (`[mcp_servers.x]`, `[plugins."x@m"]`).
    Only header lines are matched; a value line is never looked at."""
    try:
        with open(path, encoding="utf-8") as f:
            lines = f.read().splitlines()
    except (OSError, UnicodeDecodeError):
        return None
    out = []
    for line in lines:
        m = _TOML_HEADER.match(line)
        if not m:
            continue
        parts = re.findall(r'"[^"]*"|\'[^\']*\'|[^.]+', m.group(1))
        parts = [p.strip().strip("\"'") for p in parts]
        if len(parts) >= 2 and parts[0] == prefix and parts[1] not in out:
            out.append(parts[1])
    return out


def _frontmatter(path):
    try:
        with open(path, encoding="utf-8") as f:
            head = f.read(4096)
    except (OSError, UnicodeDecodeError):
        return {}
    m = re.match(r"^---\n(.*?)\n---", head, re.S)
    out = {}
    if m:
        for line in m.group(1).splitlines():
            kv = re.match(r"^(name|description):\s*(.*)$", line)
            if kv:
                out[kv.group(1)] = kv.group(2).strip().strip("\"'")
    return out


def host_sources(home):
    """(source, host, kind, reader) for every host file the scan knows. The paths live here only."""
    lib = os.path.join(home, "Library", "Application Support")
    return [
        ("scan-claude-code", "claude-code", "plugin",
         lambda: [n.split("@")[0] for n in (_json_keys(os.path.join(home, ".claude", "plugins", "installed_plugins.json"),
                                                       ("plugins",)) or [])]
         if os.path.isfile(os.path.join(home, ".claude", "plugins", "installed_plugins.json")) else None),
        ("scan-claude-code", "claude-code", "mcp",
         lambda: _json_keys(os.path.join(home, ".claude.json"), ("mcpServers",), ("projects", "*", "mcpServers"))),
        ("scan-claude-desktop", "claude-desktop", "mcp",
         lambda: _json_keys(os.path.join(lib, "Claude", "claude_desktop_config.json"), ("mcpServers",))
         if os.path.isfile(os.path.join(lib, "Claude", "claude_desktop_config.json"))
         else _json_keys(os.path.join(home, ".config", "Claude", "claude_desktop_config.json"), ("mcpServers",))),
        ("scan-codex", "codex", "mcp", lambda: _toml_tables(os.path.join(home, ".codex", "config.toml"), "mcp_servers")),
        ("scan-codex", "codex", "plugin",
         lambda: [n.split("@")[0] for n in (_toml_tables(os.path.join(home, ".codex", "config.toml"), "plugins") or [])]
         if os.path.isfile(os.path.join(home, ".codex", "config.toml")) else None),
    ]


SKILL_DIRS = ((".claude/skills", "claude-code"), (".codex/skills", "codex"), (".agents/skills", "agents"))


def scan_rows(home, apps=True, apps_jsonl=None):
    rows, read = [], []
    for source, host, kind, reader in host_sources(home):
        names = reader()
        if names is None:
            continue
        if source not in read:
            read.append(source)
        for n in names:
            n = clean(n, MAX_NAME)
            if n and norm(n) != norm(SELF):
                rows.append({"source": source, "host": host, "kind": kind, "name": n})
    for rel, host in SKILL_DIRS:
        base = os.path.join(home, rel)
        if not os.path.isdir(base):
            continue
        src = "scan-" + host if host != "agents" else "scan-agents"
        if src not in read:
            read.append(src)
        for sk in sorted(glob.glob(os.path.join(base, "*", "SKILL.md"))):
            fm = _frontmatter(sk)
            name = clean(fm.get("name") or os.path.basename(os.path.dirname(sk)), MAX_NAME)
            if name and norm(name) != norm(SELF):
                rows.append({"source": src, "host": host, "kind": "skill", "name": name,
                             "description": clean(fm.get("description"), MAX_DESC)})
    if apps:
        matched = match_apps(app_lines(apps_jsonl), load_seed())
        read.append("scan-apps")
        rows.extend(matched)
    return rows, read


def app_lines(apps_jsonl=None):
    """The JSON lines of landscape_scan.sh (never with --bookmarks), or of a file standing in for it."""
    if apps_jsonl:
        try:
            with open(apps_jsonl, encoding="utf-8") as f:
                text = f.read()
        except OSError:
            return []
    else:
        sh = os.path.join(HERE, "landscape_scan.sh")
        try:
            text = subprocess.run(["sh", sh], capture_output=True, text=True, timeout=120).stdout
        except (OSError, subprocess.SubprocessError):
            return []
    out = []
    for line in text.splitlines():
        try:
            d = json.loads(line)
        except ValueError:
            continue
        if isinstance(d, dict) and d.get("source") in ("scan-mac", "scan-iphone-on-mac"):
            out.append(d)
    return out


def match_apps(lines, seed):
    out, seen = [], set()
    for d in lines:
        nm, bid = norm(d.get("name")), str(d.get("bundle_id") or "")
        for r in seed:
            names = {norm(x) for x in r.get("app_names") or []}
            bids = set(r.get("app_bundle_ids") or [])
            if (nm and nm in names) or (bid and bid in bids):
                if r["id"] not in seen:
                    seen.add(r["id"])
                    out.append({"source": "scan-apps", "host": "standalone", "kind": "app", "name": r["name"],
                                "id": r["id"]})
                break
    return out


# ------------------------------------------------------------------ seed, store
REQUIRED = ("id", "name", "kind", "job", "skills", "access", "connect")


def check_seed(root):
    """Errors of references/tools-seed.yaml for validate-consistency.sh check 23 — one line each, [] when sound."""
    errs = []
    try:
        with open(os.path.join(root, "references", "tools-seed.yaml"), encoding="utf-8") as f:
            recs = cc.read_yaml_records(f.read(), "tools")
    except OSError:
        return ["references/tools-seed.yaml is missing"]
    except ValueError as e:
        return ["references/tools-seed.yaml does not parse: %s" % e]
    if not recs:
        return ["references/tools-seed.yaml has no tools"]
    skills = {os.path.basename(os.path.dirname(p)) for p in glob.glob(os.path.join(root, "skills", "*", "SKILL.md"))}
    seen, names = set(), set()
    for r in recs:
        rid = r.get("id") or "?"
        for k in REQUIRED:
            if r.get(k) in (None, "", []):
                errs.append("%s: no %s" % (rid, k))
        if rid in seen:
            errs.append("%s: id twice" % rid)
        seen.add(rid)
        for k, allowed in (("kind", KINDS), ("access", ACCESS), ("publishes", PUBLISHES)):
            if r.get(k) and r[k] not in allowed:
                errs.append("%s: %s %r is not one of %s" % (rid, k, r[k], "|".join(allowed)))
        for s in r.get("skills") or []:
            if s not in skills:
                errs.append("%s: %r is not a skill" % (rid, s))
        for k in ("skills", "contours", "aliases", "app_names", "app_bundle_ids"):
            if r.get(k) not in (None, "") and not isinstance(r.get(k), list):
                errs.append("%s: %s is not a list" % (rid, k))
        names |= {norm(x) for x in [rid, r.get("name")] + list(r.get("aliases") or [])}
    try:
        with open(os.path.join(root, ".mcp.json"), encoding="utf-8") as f:
            declared = list((json.load(f).get("mcpServers") or {}).keys())
    except (OSError, ValueError):
        declared = []
    for k in declared:
        if norm(k) not in names:
            errs.append("the declared connector %r (.mcp.json) has no seed record" % k)
    return errs


def load_seed():
    try:
        with open(SEED, encoding="utf-8") as f:
            return cc.read_yaml_records(f.read(), "tools")
    except (OSError, ValueError):
        return []


def store_dir(args):
    if args.store:
        return os.path.abspath(os.path.expanduser(args.store))
    return os.path.join(home_dir(args), ".grow-pm", "knowledge-library", "tools")


def home_dir(args):
    return os.path.abspath(os.path.expanduser(args.home)) if args.home else os.path.expanduser("~")


def load_registry(store):
    p = os.path.join(store, "registry.json")
    try:
        with open(p, encoding="utf-8") as f:
            data = json.load(f)
        tools = data.get("tools") if isinstance(data, dict) else None
        return [t for t in tools if isinstance(t, dict) and t.get("id")] if isinstance(tools, list) else []
    except (OSError, ValueError):
        return []


def load_team(store):
    out = []
    for p in sorted(glob.glob(os.path.join(store, "team", "*.json"))):
        try:
            with open(p, encoding="utf-8") as f:
                data = json.load(f)
        except (OSError, ValueError):
            continue
        for t in data.get("tools") or []:
            if isinstance(t, dict) and t.get("name"):
                out.append(t)
    return out


def _write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(text)
    os.replace(tmp, path)


def save(store, tools):
    tools = sorted(tools, key=lambda t: (norm(t.get("name")), t["id"]))
    _write(os.path.join(store, "registry.json"),
           json.dumps({"schema": SCHEMA, "updated": today(), "tools": tools}, ensure_ascii=False, indent=1) + "\n")
    _write(os.path.join(store, "tools.md"), render(tools, load_team(store)))


def _cell(v):
    if isinstance(v, list):
        v = ", ".join(str(x) for x in v)
    return str(v if v not in (None, "") else "—").replace("|", "/").replace("\n", " ")


def render(tools, team):
    lines = ["# Tools registry", "",
             "> Written by scripts/tools_scan.py (references/tool-registry.md). Updated %s. Records: %d." % (today(), len(tools)),
             "", "| Name | Kind | State | Verdict | For | How to connect | Seen |", "|---|---|---|---|---|---|---|"]
    for t in tools:
        lines.append("| %s | %s | %s | %s | %s | %s | %s |" % tuple(_cell(x) for x in (
            t.get("name"), t.get("kind"), t.get("state"), t.get("verdict"), t.get("skills"), t.get("connect"),
            t.get("seen"))))
    if team:
        lines += ["", "## Від команди", "", "| Name | Kind | For | How to connect | From |", "|---|---|---|---|---|"]
        for t in sorted(team, key=lambda x: norm(x.get("name"))):
            lines.append("| %s | %s | %s | %s | %s |" % tuple(_cell(x) for x in (
                t.get("name"), t.get("kind"), t.get("skills"), t.get("connect"), t.get("recommended_by"))))
    return "\n".join(lines) + "\n"


def index(tools):
    """norm(name|id|alias) -> record."""
    out = {}
    for t in tools:
        for k in [t.get("id"), t.get("name")] + list(t.get("aliases") or []):
            if norm(k) and norm(k) not in out:
                out[norm(k)] = t
    return out


def new_id(name, tools):
    base = cc.slugify(name)[:60] or "tool"
    ids, cand, i = {t["id"] for t in tools}, base, 2
    while cand in ids:
        cand, i = "%s-%d" % (base, i), i + 1
    return cand


def never(record_fields):
    """Kinds of a value the never-store filter refuses, per field — never the value."""
    bad = {}
    for k, v in record_fields.items():
        texts = v if isinstance(v, list) else [v]
        kinds = []
        for x in texts:
            if isinstance(x, str):
                for kind in cn.scan(x):
                    if kind not in kinds:
                        kinds.append(kind)
        if kinds:
            bad[k] = kinds
    return bad


def _add_unique(lst, *vals):
    lst = list(lst or [])
    for v in vals:
        if v and v not in lst:
            lst.append(v)
    return lst


# ------------------------------------------------------------------ commands
def read_rows(path):
    rows, read = [], []
    if not path:
        return rows, read
    text = sys.stdin.read() if path == "-" else open(path, encoding="utf-8").read()
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("TOOLS_RESULT "):
            try:
                read.extend(json.loads(line[len("TOOLS_RESULT "):]).get("sources_read") or [])
            except ValueError:
                pass
            continue
        try:
            d = json.loads(line)
        except ValueError:
            continue
        if isinstance(d, dict) and d.get("name"):
            rows.append(d)
    return rows, read


def cmd_scan(args):
    rows, read = scan_rows(home_dir(args), apps=not args.no_apps, apps_jsonl=args.apps_jsonl)
    for r in rows:
        print(json.dumps(r, ensure_ascii=False, sort_keys=True))
    by = {}
    for r in rows:
        by[r["source"]] = by.get(r["source"], 0) + 1
    result(found=len(rows), by_source=by, sources_read=read)
    return 0


def cmd_merge(args):
    store = store_dir(args)
    tools = load_registry(store)
    seed = load_seed()
    idx = index(tools)
    added_seed = 0
    for s in seed:
        if norm(s["id"]) in idx or norm(s.get("name")) in idx:
            rec = idx.get(norm(s["id"])) or idx.get(norm(s.get("name")))
            for k in SEED_FIELDS + ("aliases",):
                if rec.get(k) in (None, "", []) and s.get(k) not in (None, "", []):
                    rec[k] = s[k]
            rec["sources"] = _add_unique(rec.get("sources"), "seed")
            continue
        rec = {"id": s["id"], "state": "not-installed", "sources": ["seed"]}
        for k in SEED_FIELDS + ("aliases",):
            if s.get(k) not in (None, "", []):
                rec[k] = s[k]
        tools.append(rec)
        idx = index(tools)
        added_seed += 1
    rows, covered = [], []
    if args.rescan:
        rows, covered = scan_rows(home_dir(args), apps=not args.no_apps, apps_jsonl=args.apps_jsonl)
    elif args.scan:
        rows, covered = read_rows(args.scan)
    obs, _ = read_rows(args.observed)
    for o in obs:
        o["source"] = o.get("source") if o.get("source") in ("scan-session", "scan-account") else "scan-session"
        covered = _add_unique(covered, o["source"])
    if args.observed:
        covered = _add_unique(covered, "scan-session")
    seen_now, created, refused = {}, 0, []
    for row in rows + obs:
        name = clean(row.get("name"), MAX_NAME)
        if not name or norm(name) == norm(SELF):
            continue
        if never({"name": name}):
            refused.append({"source": row.get("source"), "kinds": never({"name": name})["name"]})
            continue
        rec = idx.get(norm(row.get("id"))) if row.get("id") else None
        rec = rec or idx.get(norm(name))
        if rec is None:
            kind = row.get("kind") if row.get("kind") in KINDS else "mcp"
            rec = {"id": new_id(name, tools), "name": name, "kind": kind, "sources": []}
            desc = clean(row.get("description"), MAX_DESC)
            if desc and not never({"job": desc}):
                rec["job"] = desc
            tools.append(rec)
            idx = index(tools)
            created += 1
        state = row.get("state") if row.get("state") in OBSERVED else "installed"
        prev = seen_now.get(rec["id"])
        seen_now[rec["id"]] = state if prev is None or RANK[state] < RANK[prev] else prev
        host = row.get("host") or ("session" if row["source"] == "scan-session" else
                                   "account" if row["source"] == "scan-account" else "")
        rec["hosts"] = _add_unique(rec.get("hosts"), host)
        rec["sources"] = _add_unique(rec.get("sources"), row["source"])
        rec.setdefault("_seen_by", [])
        rec["_seen_by"] = _add_unique(rec["_seen_by"], row["source"])
    stamp, changed_state = today(), 0
    for rec in tools:
        now = rec.pop("_seen_by", None)
        if rec["id"] in seen_now:
            new = seen_now[rec["id"]]
            changed_state += new != rec.get("state")
            rec["state"], rec["seen"], rec["seen_by"] = new, stamp, now
        elif rec.get("state") in OBSERVED and rec.get("seen_by") and set(rec["seen_by"]) <= set(covered):
            rec["state"] = "not-seen"
            changed_state += 1
        elif not rec.get("state"):
            rec["state"] = "not-installed"
    try:
        save(store, tools)
        if rows or obs:
            os.makedirs(os.path.join(store, "scans"), exist_ok=True)
            with open(os.path.join(store, "scans", "%s.jsonl" % stamp), "a", encoding="utf-8") as f:
                for r in rows + obs:
                    keep = {k: r[k] for k in ("source", "host", "kind", "name", "state", "id") if r.get(k)}
                    f.write(json.dumps(keep, ensure_ascii=False, sort_keys=True) + "\n")
    except OSError as e:
        result(error="store not writable: %s" % (e.strerror or e), store=store)
        return 1
    result(store=store, records=len(tools), seed_added=added_seed, created=created, observed=len(seen_now),
           state_changed=changed_state, sources_covered=sorted(covered), refused=refused)
    return 0


def _candidates(store, skill):
    own = load_registry(store)
    team = load_team(store)
    own_idx = index(own)
    order = {s["id"]: i for i, s in enumerate(load_seed())}      # the seed lists the likeliest tool first
    team_names = {norm(t.get("name")) for t in team}
    cands = []
    for t in own:
        cands.append((t, "own"))
    for t in team:
        if norm(t.get("name")) not in own_idx:
            cands.append((t, "team"))
    out = []
    for t, origin in cands:
        if skill not in (t.get("skills") or []):
            continue
        if t.get("state") in ("installed", "connected"):
            continue
        if t.get("verdict") == "deprecated":
            continue
        if any(isinstance(d, dict) and d.get("skill") == skill for d in t.get("declined") or []):
            continue
        rank = 0 if (origin == "own" and t.get("verdict") == "recommended") else \
            1 if origin == "team" or str(t.get("recommended_by", "")).startswith("team:") or \
            norm(t.get("name")) in team_names else \
            2 if "seed" in (t.get("sources") or []) else 3
        primary = (t.get("skills") or []).index(skill)            # a tool that names the skill first serves it first
        out.append((rank, primary, order.get(t.get("id"), len(order)), norm(t.get("name")), t, origin))
    return sorted(out, key=lambda x: x[:4])


def cmd_suggest(args):
    store = store_dir(args)
    if not os.path.isfile(os.path.join(store, "registry.json")) and not load_team(store):
        result(suggest=None, why="no registry")
        return 0
    c = _candidates(store, args.skill)
    if not c:
        result(suggest=None)
        return 0
    t, origin = c[0][4], c[0][5]
    print(json.dumps({"id": t.get("id") or cc.slugify(t.get("name")), "name": t.get("name"), "job": t.get("job", ""),
                      "connect": t.get("connect", ""), "state": t.get("state", "not-installed"), "origin": origin},
                     ensure_ascii=False, sort_keys=True))
    result(suggest=t.get("id") or cc.slugify(t.get("name")), origin=origin)
    return 0


def _find(tools, key):
    for t in tools:
        if t["id"] == key:
            return t
    return index(tools).get(norm(key))


def cmd_decline(args):
    store = store_dir(args)
    tools = load_registry(store)
    rec = _find(tools, args.id)
    if rec is None:
        team = [t for t in load_team(store) if norm(t.get("name")) == norm(args.id) or
                cc.slugify(t.get("name")) == args.id]
        if not team:
            result(error="no record %s" % args.id)
            return 2
        rec = _from_team(team[0], tools)
        tools.append(rec)
    if args.undo:
        rec["declined"] = [d for d in rec.get("declined") or [] if d.get("skill") != args.skill]
    elif not any(d.get("skill") == args.skill for d in rec.get("declined") or []):
        rec["declined"] = list(rec.get("declined") or []) + [{"skill": args.skill, "date": today()}]
    try:
        save(store, tools)
    except OSError as e:
        result(error="store not writable: %s" % (e.strerror or e))
        return 1
    result(id=rec["id"], skill=args.skill, declined=not args.undo)
    return 0


def _parse_fields(pairs):
    out, bad = {}, []
    for p in pairs or []:
        if "=" not in p:
            bad.append(p)
            continue
        k, v = p.split("=", 1)
        k, v = k.strip(), v.strip()
        if k not in USER_FIELDS:
            bad.append(k)
            continue
        if k in LIST_FIELDS:
            out[k] = [x.strip() for x in v.split(",") if x.strip()]
        elif k == "shared":
            out[k] = v.lower() in ("true", "yes", "1", "так")
        elif k == "verdict" and v and v not in VERDICTS:
            bad.append("verdict=" + v)
        elif k == "access" and v and v not in ACCESS:
            bad.append("access=" + v)
        elif k == "publishes" and v and v not in PUBLISHES:
            bad.append("publishes=" + v)
        else:
            out[k] = clean(v)
    return out, bad


def _from_team(t, tools):
    rec = {"id": new_id(t.get("name"), tools), "sources": [], "state": "not-installed"}
    for k in EXPORT_FIELDS:
        if t.get(k) not in (None, "", []):
            rec[k] = t[k]
    rec["sources"] = _add_unique(rec["sources"], str(t.get("recommended_by") or "team"))
    return rec


def _apply(rec, fields, tools, store, what):
    bad = never(fields)
    if bad:
        result(error="refused", refused=[{"field": k, "kinds": v} for k, v in bad.items()])
        return 2
    for k, v in fields.items():
        if v in ("", []):
            rec.pop(k, None)
        else:
            rec[k] = v
    try:
        save(store, tools)
    except OSError as e:
        result(error="store not writable: %s" % (e.strerror or e))
        return 1
    result(id=rec["id"], **{what: sorted(fields)})
    return 0


def cmd_add(args):
    store = store_dir(args)
    tools = load_registry(store)
    if args.from_team:
        team = [t for t in load_team(store) if norm(t.get("name")) == norm(args.from_team) or
                cc.slugify(t.get("name")) == args.from_team]
        if not team:
            result(error="no team record %s" % args.from_team)
            return 2
        if _find(tools, team[0].get("name")):
            result(error="already in the registry", id=_find(tools, team[0].get("name"))["id"])
            return 2
        rec = _from_team(team[0], tools)
        tools.append(rec)
        return _apply(rec, {}, tools, store, "added")
    if not args.name or args.kind not in KINDS:
        result(error="add needs --name and --kind (%s)" % "|".join(KINDS))
        return 2
    if _find(tools, args.name):
        result(error="already in the registry", id=_find(tools, args.name)["id"])
        return 2
    fields, bad = _parse_fields(args.fields)
    if bad:
        result(error="unknown or invalid fields", fields=bad)
        return 2
    if never({"name": args.name}):
        result(error="refused", refused=[{"field": "name", "kinds": never({"name": args.name})["name"]}])
        return 2
    rec = {"id": new_id(args.name, tools), "name": clean(args.name, MAX_NAME), "kind": args.kind,
           "state": "not-installed", "sources": [args.source]}
    tools.append(rec)
    return _apply(rec, fields, tools, store, "added")


def cmd_set(args):
    store = store_dir(args)
    tools = load_registry(store)
    rec = _find(tools, args.id)
    if rec is None:
        result(error="no record %s" % args.id)
        return 2
    fields, bad = _parse_fields(args.fields)
    if bad or not fields:
        result(error="unknown or invalid fields", fields=bad or ["(none given)"])
        return 2
    return _apply(rec, fields, tools, store, "set")


def cmd_team(args):
    import ctx_repos as cr
    import provider_bundle as pb
    home = home_dir(args)
    store = store_dir(args)
    ctx_path = cc.find_context(args.context, home=home)
    text = ""
    if ctx_path:
        with open(ctx_path, encoding="utf-8") as f:
            text = f.read()
    skipped, read, why = [], {}, []
    repos = cr.load_repos(text, home, skipped=skipped)
    for repo in repos:
        root = repo.get("core_root")
        if not root or not os.path.isdir(root):
            continue
        m, said = pb.read_manifest(root)
        if m is None or not m.s("tools_file"):
            continue
        rel = str(m.s("tools_file"))
        path = os.path.realpath(os.path.join(root, rel))
        if not (path + os.sep).startswith(os.path.realpath(root) + os.sep) or not os.path.isfile(path):
            why.append({"core": repo["id"], "why": "tools_file outside the core or missing"})
            continue
        try:
            with open(path, encoding="utf-8") as f:
                recs = cc.read_yaml_records(f.read(), "tools")
        except (OSError, ValueError, UnicodeDecodeError) as e:
            why.append({"core": repo["id"], "why": "tools_file unreadable: %s" % str(e)[:120]})
            continue
        kept = []
        for r in recs:
            rec = {k: r[k] for k in EXPORT_FIELDS if r.get(k) not in (None, "", [])}
            if not rec.get("name") or never(rec):
                continue
            rec["recommended_by"] = "team:%s" % repo["id"]
            kept.append(rec)
        try:
            _write(os.path.join(store, "team", "%s.json" % cc.slugify(repo["id"])),
                   json.dumps({"core": repo["id"], "read": today(), "tools": kept}, ensure_ascii=False, indent=1) + "\n")
        except OSError as e:
            result(error="store not writable: %s" % (e.strerror or e))
            return 1
        read[repo["id"]] = len(kept)
    if read:
        try:
            _write(os.path.join(store, "tools.md"), render(load_registry(store), load_team(store)))
        except OSError:
            pass
    result(team=read, skipped=why, registrations_skipped=len(skipped))
    return 0


def _yaml_scalar(v):
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, list):
        return "[" + ", ".join(json.dumps(str(x), ensure_ascii=False) for x in v) + "]"
    return json.dumps(str(v), ensure_ascii=False)


def cmd_export(args):
    store = store_dir(args)
    tools = [t for t in load_registry(store) if t.get("shared") is True]
    lines = ["# Tools shared from a Grow PM tools registry (references/tool-registry.md §5).",
             "# Put this file in the core and name its path in the provider manifest: tools_file: <path>.",
             "tools:"]
    for t in sorted(tools, key=lambda x: norm(x.get("name"))):
        first = True
        for k in EXPORT_FIELDS:
            v = t.get(k)
            if k == "recommended_by" and not v:
                v = ""
            if v in (None, "", []):
                continue
            lines.append(("  - " if first else "    ") + "%s: %s" % (k, _yaml_scalar(v)))
            first = False
    path = os.path.join(store, "export", "tools-shared-%s.yaml" % today())
    try:
        _write(path, "\n".join(lines) + "\n")
    except OSError as e:
        result(error="store not writable: %s" % (e.strerror or e))
        return 1
    result(exported=len(tools), file=path)
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(prog="tools_scan.py", description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd")

    def common(p):
        p.add_argument("--store", help="the registry folder (default ~/.grow-pm/knowledge-library/tools)")
        p.add_argument("--home", help="the home whose host files are read (default the user's)")
        return p

    p = common(sub.add_parser("scan"))
    p.add_argument("--no-apps", action="store_true")
    p.add_argument("--apps-jsonl", help=argparse.SUPPRESS)
    p = common(sub.add_parser("merge"))
    p.add_argument("--scan")
    p.add_argument("--observed")
    p.add_argument("--rescan", action="store_true")
    p.add_argument("--no-apps", action="store_true")
    p.add_argument("--apps-jsonl", help=argparse.SUPPRESS)
    p = common(sub.add_parser("suggest"))
    p.add_argument("--skill", required=True)
    p = common(sub.add_parser("decline"))
    p.add_argument("--skill", required=True)
    p.add_argument("--id", required=True)
    p.add_argument("--undo", action="store_true")
    p = common(sub.add_parser("add"))
    p.add_argument("--name")
    p.add_argument("--kind")
    p.add_argument("--from-team")
    p.add_argument("--source", choices=("user", "registry-search", "catalog"), default="user")
    p.add_argument("fields", nargs="*")
    p = common(sub.add_parser("set"))
    p.add_argument("--id", required=True)
    p.add_argument("fields", nargs="*")
    p = common(sub.add_parser("team"))
    p.add_argument("--context")
    common(sub.add_parser("export"))
    args = ap.parse_args(argv)
    fn = {"scan": cmd_scan, "merge": cmd_merge, "suggest": cmd_suggest, "decline": cmd_decline, "add": cmd_add,
          "set": cmd_set, "team": cmd_team, "export": cmd_export}.get(args.cmd)
    if fn is None:
        ap.print_help()
        return 2
    return fn(args)


if __name__ == "__main__":
    sys.exit(main())
