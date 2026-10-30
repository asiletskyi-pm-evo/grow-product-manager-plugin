#!/usr/bin/env python3
"""tools_scan.py — the tools registry of knowledge-library (references/tool-registry.md).

  scan     the names of what is installed on this machine, one JSON line each
  merge    seed + scan + observed rows -> registry.json, tools.md, scans/<date>.jsonl
  suggest  at most one record a skill may offer at its step
  decline  the user's «ні» to a suggestion in one skill (--undo takes it back)
  add      a record by hand, a search result the user picked, or a team's record taken over (--from-team)
  set      the user's own fields of a record
  team     the lists the user's cores publish (`tools_file`), read-only
  export   the records the user marked shared, one file for a core's owner

Names only: from a host's configuration the scan takes the keys of its MCP server map and the table
headers and keys of a TOML file — never a value (command, args, env, headers, url); lines inside a
multi-line string or array are never looked at. Every text written passes the never-store filter
(ctx_never). Every command ends with one `TOOLS_RESULT {json}` line. Stdlib only (Python 3.9).
Exit 0; 2 for wrong arguments, an unknown record or an unreadable input; 1 when the store cannot be
written or its registry.json exists but does not read (it is never reset).
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
STANDALONE_KINDS = ("app", "site", "cli", "portal", "course")      # an installed app counts for these
ACCESS = ("free", "paid", "corporate", "unknown")
VERDICTS = ("tried", "recommended", "deprecated")
PUBLISHES = ("board", "page", "document", "deck", "dashboard", "design")
CONTOURS = ("product", "delivery", "knowledge", "people", "design", "context")
STATES = ("connected", "needs-auth", "installed", "not-installed", "not-seen")
OBSERVED = ("connected", "needs-auth", "installed")
RANK = {s: i for i, s in enumerate(STATES)}
SOURCE_HOST = {
    "scan-claude-code-plugins": "claude-code", "scan-claude-code-mcp": "claude-code",
    "scan-claude-code-skills": "claude-code", "scan-claude-desktop": "claude-desktop",
    "scan-codex-mcp": "codex", "scan-codex-plugins": "codex", "scan-codex-skills": "codex",
    "scan-agents-skills": "agents", "scan-apps": "standalone", "scan-session": "session", "scan-account": "account"}
SEED_FIELDS = ("name", "kind", "job", "skills", "contours", "access", "connect", "publishes", "via", "needs")
USER_FIELDS = ("verdict", "shared", "recommended_by", "connect", "job", "access", "skills", "contours",
               "publishes", "checked", "notes")
LIST_FIELDS = ("skills", "contours")
EXPORT_FIELDS = ("name", "kind", "job", "skills", "contours", "access", "connect", "verdict", "recommended_by",
                 "checked", "publishes")
MAX_NAME, MAX_TEXT, MAX_DESC, MAX_FILE = 120, 300, 200, 64 * 1024 * 1024
KEEP_SCANS = 30
NAME_RE = re.compile(r"^[^\W_][\w .@+:()/'-]*$")
OPAQUE_RE = re.compile(r"^(?:[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}|[0-9a-f]{24,})$", re.I)
FOLDED = (">", "|", ">-", "|-", ">+", "|+")


def today():
    return datetime.date.today().isoformat()


def norm(s):
    return re.sub(r"[^a-z0-9]", "", str(s or "").lower())


def clean(s, limit=MAX_TEXT):
    s = re.sub(r"[\x00-\x1f\x7f]+", " ", str(s or "")).strip()
    return s[:limit]


def result(**kw):
    print("TOOLS_RESULT " + json.dumps(kw, ensure_ascii=False, sort_keys=True))


def flagged(text):
    """Kinds of a value the never-store filter refuses in `text` (before any cut) — never the value."""
    return cn.scan(text) if isinstance(text, str) else []


def valid_name(raw):
    """A name the registry may keep, or "" — checked whole before it is cut: never a value that looks like a key,
    an opaque id, the plugin itself or one of its skills."""
    if not isinstance(raw, str) or flagged(raw):
        return ""
    n = clean(raw, MAX_NAME + 1)
    if not n or len(n) > MAX_NAME or not NAME_RE.match(n) or OPAQUE_RE.match(n):
        return ""
    if norm(n) == norm(SELF) or n.lower().startswith(SELF + ":"):
        return ""
    return n


def skill_names():
    return {os.path.basename(os.path.dirname(p)) for p in glob.glob(os.path.join(ROOT, "skills", "*", "SKILL.md"))}


# ------------------------------------------------------------------ host files (names only)
def _read_bounded(path):
    try:
        if not path or not os.path.isfile(path) or os.path.getsize(path) > MAX_FILE:
            return None
        with open(path, encoding="utf-8") as f:
            return f.read()
    except (OSError, UnicodeDecodeError):
        return None


def _json_keys(path, *ways):
    """The keys of the maps found at `ways` (tuples of keys; '*' walks every value) in a JSON file — never a value."""
    text = _read_bounded(path)
    if text is None:
        return None
    try:
        data = json.loads(text)
    except ValueError:
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


_KEY = r"""(?:"[^"\\]*(?:\\.[^"\\]*)*"|'[^']*'|[A-Za-z0-9_-]+)"""
_DOTTED = re.compile(r"^\s*(%s(?:\s*\.\s*%s)*)\s*=\s*(.*)$" % (_KEY, _KEY))
_HEADER = re.compile(r"^\s*\[\s*([^\[\]]+?)\s*\]\s*(?:#.*)?$")
_AHEADER = re.compile(r"^\s*\[\[\s*([^\[\]]+?)\s*\]\]\s*(?:#.*)?$")


def _key_parts(s):
    return [p.strip().strip("\"'") for p in re.findall(r'"[^"]*"|\'[^\']*\'|[^.]+', s)]


def _brackets(s):
    """The bracket balance of a TOML value outside its strings; a comment ends it."""
    depth, q, i = 0, None, 0
    while i < len(s):
        ch = s[i]
        if q:
            if ch == "\\" and q == '"':
                i += 2
                continue
            if ch == q:
                q = None
        elif ch in "\"'":
            q = ch
        elif ch == "#":
            break
        elif ch in "[{":
            depth += 1
        elif ch in "]}":
            depth -= 1
        i += 1
    return depth


def _toml_names(path, prefix):
    """The names right under `prefix` in a TOML file — `[prefix.x]`, `[[prefix.x.y]]`, `prefix.x.k = …`,
    `x = …` / `x.k = …` inside `[prefix]` — read from table headers and keys only. A line inside a
    multi-line string or array is skipped whole, so a value that looks like a header is never a name."""
    text = _read_bounded(path)
    if text is None:
        return None
    out, table, ml, depth = [], [], None, 0
    for line in text.splitlines():
        if ml:
            if line.count(ml) % 2 == 1:
                ml = None
            continue
        if depth > 0:
            depth = max(0, depth + _brackets(line))
            continue
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        m = _AHEADER.match(line) or _HEADER.match(line)
        if m:
            table = _key_parts(m.group(1))
            if len(table) >= 2 and table[0] == prefix and table[1] not in out:
                out.append(table[1])
            continue
        m = _DOTTED.match(line)
        if not m:
            continue
        full = table + _key_parts(m.group(1))
        if len(full) >= 2 and full[0] == prefix and full[1] not in out:
            out.append(full[1])
        val = m.group(2)
        for q in ('"""', "'''"):
            if val.count(q) % 2 == 1:
                ml = q
                break
        if not ml:
            depth = max(0, _brackets(val))
    return out


def _frontmatter(path):
    try:
        with open(path, encoding="utf-8") as f:
            head = f.read(4096)
    except (OSError, UnicodeDecodeError):
        return {}
    lines = head.split("\n")
    if not lines or lines[0].strip() != "---":
        return {}
    end = next((i for i in range(1, min(len(lines), 30)) if lines[i].strip() == "---"), None)
    if end is None:
        return {}
    out = {}
    for line in lines[1:end]:
        kv = re.match(r"^(name|description):\s*(.*)$", line)
        if kv:
            v = kv.group(2).strip().strip("\"'")
            if v and v not in FOLDED:
                out[kv.group(1)] = v
    return out


def host_readers(home):
    """(source, kind, reader) for every host file the scan knows. The paths live here only."""
    lib = os.path.join(home, "Library", "Application Support", "Claude", "claude_desktop_config.json")
    xdg = os.path.join(home, ".config", "Claude", "claude_desktop_config.json")
    codex = os.path.join(home, ".codex", "config.toml")

    def plugins_of(names):
        return None if names is None else [n.split("@")[0] for n in names]
    return [
        ("scan-claude-code-plugins", "plugin",
         lambda: plugins_of(_json_keys(os.path.join(home, ".claude", "plugins", "installed_plugins.json"), ("plugins",)))),
        ("scan-claude-code-mcp", "mcp",
         lambda: _json_keys(os.path.join(home, ".claude.json"), ("mcpServers",), ("projects", "*", "mcpServers"))),
        ("scan-claude-desktop", "mcp",
         lambda: _json_keys(lib if os.path.isfile(lib) else xdg, ("mcpServers",))),
        ("scan-codex-mcp", "mcp", lambda: _toml_names(codex, "mcp_servers")),
        ("scan-codex-plugins", "plugin", lambda: plugins_of(_toml_names(codex, "plugins"))),
    ]


SKILL_DIRS = ((".claude/skills", "scan-claude-code-skills"), (".codex/skills", "scan-codex-skills"),
              (".agents/skills", "scan-agents-skills"))


def scan_rows(home, apps=True, apps_jsonl=None):
    """(rows, sources read, refused) — `read` names a source only when its file was there and read."""
    rows, read, refused = [], [], 0
    for source, kind, reader in host_readers(home):
        names = reader()
        if names is None:
            continue
        read.append(source)
        for raw in names:
            n = valid_name(raw)
            if n:
                rows.append({"source": source, "host": SOURCE_HOST[source], "kind": kind, "name": n})
            elif raw and norm(raw) != norm(SELF):
                refused += 1
    for rel, source in SKILL_DIRS:
        base = os.path.join(home, rel)
        if not os.path.isdir(base):
            continue
        read.append(source)
        for sk in sorted(glob.glob(os.path.join(base, "*", "SKILL.md"))):
            fm = _frontmatter(sk)
            raw = fm.get("name") or os.path.basename(os.path.dirname(sk))
            n = valid_name(raw)
            if not n:
                refused += norm(raw) != norm(SELF)
                continue
            row = {"source": source, "host": SOURCE_HOST[source], "kind": "skill", "name": n}
            desc = fm.get("description") or ""
            if desc and not flagged(desc):
                row["description"] = clean(desc, MAX_DESC)
            rows.append(row)
    if apps:
        lines, ok = app_lines(apps_jsonl)
        if ok:
            read.append("scan-apps")
            rows.extend(match_apps(lines, load_seed()))
    return rows, read, refused


def app_lines(apps_jsonl=None):
    """(the scan-mac / scan-iphone-on-mac lines of landscape_scan.sh — never run with --bookmarks — or of a file
    standing in for it, whether it ran: exit 0 and at least one app line)."""
    if apps_jsonl:
        text = _read_bounded(apps_jsonl)
        if text is None:
            return [], False
    else:
        try:
            p = subprocess.run(["sh", os.path.join(HERE, "landscape_scan.sh")], capture_output=True, text=True,
                               timeout=120)
        except (OSError, subprocess.SubprocessError):
            return [], False
        if p.returncode != 0:
            return [], False
        text = p.stdout
    out = []
    for line in text.splitlines():
        try:
            d = json.loads(line)
        except ValueError:
            continue
        if isinstance(d, dict) and d.get("source") in ("scan-mac", "scan-iphone-on-mac"):
            out.append(d)
    return out, bool(out)


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
    ids = [r.get("id") for r in recs]
    owner, twice = {}, set()
    for r in recs:
        rid = r.get("id") or "?"
        for k in REQUIRED:
            if r.get(k) in (None, "", []):
                errs.append("%s: no %s" % (rid, k))
        if ids.count(rid) > 1 and rid not in twice:
            twice.add(rid)
            errs.append("%s: id twice" % rid)
        for k, allowed in (("kind", KINDS), ("access", ACCESS), ("publishes", PUBLISHES)):
            if r.get(k) not in (None, "") and r[k] not in allowed:
                errs.append("%s: %s %r is not one of %s" % (rid, k, r[k], "|".join(allowed)))
        for k in ("skills", "contours", "aliases", "app_names", "app_bundle_ids", "needs"):
            if r.get(k) not in (None, "") and not isinstance(r.get(k), list):
                errs.append("%s: %s is not a list" % (rid, k))
        for s in r.get("skills") or []:
            if s not in skills:
                errs.append("%s: %r is not a skill" % (rid, s))
        for c in r.get("contours") or []:
            if c not in CONTOURS:
                errs.append("%s: contour %r is not one of %s" % (rid, c, "|".join(CONTOURS)))
        if r.get("via") and r["via"] not in ids:
            errs.append("%s: via %r is not a seed record" % (rid, r["via"]))
        for key in {norm(x) for x in [rid, r.get("name")] + list(r.get("aliases") or []) if norm(x)}:
            if key in owner and owner[key] != rid:
                errs.append("%s: name or alias %r is also %s's" % (rid, key, owner[key]))
            owner.setdefault(key, rid)
    try:
        with open(os.path.join(root, ".mcp.json"), encoding="utf-8") as f:
            declared = list((json.load(f).get("mcpServers") or {}).keys())
    except (OSError, ValueError):
        declared = []
    for k in declared:
        if norm(k) not in owner:
            errs.append("the declared connector %r (.mcp.json) has no seed record" % k)
    return errs


def load_seed():
    try:
        with open(SEED, encoding="utf-8") as f:
            return cc.read_yaml_records(f.read(), "tools")
    except (OSError, ValueError):
        return []


def home_dir(args):
    return os.path.abspath(os.path.expanduser(args.home)) if args.home else os.path.expanduser("~")


def store_dir(args):
    if args.store:
        return os.path.abspath(os.path.expanduser(args.store))
    return os.path.join(home_dir(args), ".grow-pm", "knowledge-library", "tools")


class Unreadable(Exception):
    pass


def load_registry(store):
    """The records of registry.json — [] when there is none; Unreadable when it is there and does not read, so that
    no command overwrites the user's verdicts, sharing and declines with an empty registry."""
    p = os.path.join(store, "registry.json")
    if not os.path.exists(p):
        return []
    text = _read_bounded(p)
    try:
        data = json.loads(text) if text is not None else None
    except ValueError:
        data = None
    tools = data.get("tools") if isinstance(data, dict) else None
    if not isinstance(tools, list):
        raise Unreadable(p)
    return [t for t in tools if isinstance(t, dict) and t.get("id")]


def load_team(store):
    out = []
    for p in sorted(glob.glob(os.path.join(store, "team", "*.json"))):
        text = _read_bounded(p)
        try:
            data = json.loads(text) if text else {}
        except ValueError:
            continue
        for t in data.get("tools") or []:
            if isinstance(t, dict) and t.get("name"):
                out.append(t)
    return out


def load_team_declined(store):
    text = _read_bounded(os.path.join(store, "team-declined.json"))
    try:
        data = json.loads(text) if text else []
    except ValueError:
        data = []
    return [d for d in data if isinstance(d, dict)] if isinstance(data, list) else []


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
             "> Written by scripts/tools_scan.py (references/tool-registry.md) — edit it through knowledge-library, "
             "not by hand. Updated %s. Records: %d." % (today(), len(tools)),
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


def never(fields):
    """Kinds of a value the never-store filter refuses, per field — never the value."""
    bad = {}
    for k, v in fields.items():
        kinds = []
        for x in (v if isinstance(v, list) else [v]):
            for kind in flagged(x):
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


def _unreadable(path):
    result(error="registry.json does not read — left as it is; restore it from the vault mirror (Knowledge/tools/) "
                 "or move it aside", file=path)
    return 1


# ------------------------------------------------------------------ commands
def read_rows(path):
    """(rows, sources read) of a file or stdin; OSError/UnicodeDecodeError go to the caller."""
    rows, read = [], []
    if not path:
        return rows, read
    if path == "-":
        text = sys.stdin.read()
    else:
        if not os.path.isfile(path):
            raise OSError(2, "no such file")
        with open(path, encoding="utf-8") as f:
            text = f.read(MAX_FILE)
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("TOOLS_RESULT "):
            try:
                read.extend(s for s in json.loads(line[len("TOOLS_RESULT "):]).get("sources_read") or []
                            if s in SOURCE_HOST)
            except (ValueError, AttributeError):
                pass
            continue
        try:
            d = json.loads(line)
        except ValueError:
            continue
        if isinstance(d, dict):
            rows.append(d)
    return rows, read


def sanitize(row, observed, seed_ids):
    """The row as the registry may keep it, or None — every field from a closed list or through the filter."""
    if not isinstance(row, dict):
        return None
    src = row.get("source")
    if observed:
        src = src if src in ("scan-session", "scan-account") else "scan-session"
    elif src not in SOURCE_HOST or src in ("scan-session", "scan-account"):
        return None
    name = valid_name(row.get("name"))
    kind = row.get("kind") if row.get("kind") in KINDS else ("mcp" if observed and not row.get("kind") else None)
    if not name or not kind:
        return None
    out = {"source": src, "host": SOURCE_HOST[src], "kind": kind, "name": name,
           "state": row.get("state") if row.get("state") in OBSERVED else "installed"}
    if src == "scan-apps" and row.get("id") in seed_ids:
        out["id"] = row["id"]
    desc = row.get("description")
    if isinstance(desc, str) and desc.strip() and desc.strip() not in FOLDED and not flagged(desc):
        out["description"] = clean(desc, MAX_DESC)
    return out


def _counts_for(row, rec):
    """Whether a row may set a record's state: the same kind, or an installed app for a standalone tool. A Zoom app
    never makes the Zoom connector `installed`, nor a skill folder named like a server that server."""
    return row["kind"] == rec.get("kind") or (row["kind"] == "app" and rec.get("kind") in STANDALONE_KINDS)


def cmd_scan(args):
    rows, read, refused = scan_rows(home_dir(args), apps=not args.no_apps, apps_jsonl=args.apps_jsonl)
    for r in rows:
        print(json.dumps(r, ensure_ascii=False, sort_keys=True))
    by = {}
    for r in rows:
        by[r["source"]] = by.get(r["source"], 0) + 1
    result(found=len(rows), by_source=by, sources_read=read, refused=refused)
    return 0


def cmd_merge(args):
    store = store_dir(args)
    try:
        tools = load_registry(store)
    except Unreadable as e:
        return _unreadable(str(e))
    seed = load_seed()
    seed_ids = {s["id"] for s in seed}
    idx = index(tools)
    added_seed = 0
    for s in seed:
        keys = [s["id"], s.get("name")] + list(s.get("aliases") or [])
        rec = next((idx[norm(k)] for k in keys if norm(k) in idx), None)
        if rec is not None:
            for k in SEED_FIELDS + ("aliases",):
                if k in (rec.get("cleared") or []):
                    continue
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
    try:
        if args.rescan:
            raw, covered, refused = scan_rows(home_dir(args), apps=not args.no_apps, apps_jsonl=args.apps_jsonl)
        else:
            raw, covered = read_rows(args.scan)
            refused = 0
        obs_raw, _ = read_rows(args.observed)
    except (OSError, UnicodeDecodeError) as e:
        result(error="input does not read: %s" % (getattr(e, "strerror", None) or type(e).__name__))
        return 2
    rows = []
    for r in raw:
        s = sanitize(r, False, seed_ids)
        if s:
            rows.append(s)
        else:
            refused += 1
    obs = []
    for r in obs_raw:
        s = sanitize(r, True, seed_ids)
        if s:
            obs.append(s)
            covered = _add_unique(covered, s["source"])
        else:
            refused += 1
    if args.observed:
        covered = _add_unique(covered, "scan-session")
    seen_now, created = {}, 0
    for row in rows + obs:
        rec = idx.get(norm(row.get("id"))) if row.get("id") else None
        rec = rec or idx.get(norm(row["name"]))
        if rec is None:
            rec = {"id": new_id(row["name"], tools), "name": row["name"], "kind": row["kind"], "sources": []}
            if row.get("description"):
                rec["job"] = row["description"]
            tools.append(rec)
            idx = index(tools)
            created += 1
        rec["hosts"] = _add_unique(rec.get("hosts"), row["host"])
        rec["sources"] = _add_unique(rec.get("sources"), row["source"])
        if not _counts_for(row, rec):
            continue
        prev = seen_now.get(rec["id"])
        best = row["state"] if prev is None or RANK[row["state"]] < RANK[prev[0]] else prev[0]
        seen_now[rec["id"]] = (best, _add_unique(prev[1] if prev else [], row["source"]))
    stamp, changed = today(), 0
    for rec in tools:
        if rec["id"] in seen_now:
            new, by = seen_now[rec["id"]]
            old = rec.get("state")
            if old in ("connected", "needs-auth") and new == "installed" and "scan-session" not in covered \
                    and "scan-session" in (rec.get("seen_by") or []):
                new = old                          # the files see it installed; the session that saw more is not here
                by = _add_unique(by, *[s for s in rec.get("seen_by") or [] if s not in covered])
            changed += new != old
            rec["state"], rec["seen"], rec["seen_by"] = new, stamp, by
        elif rec.get("state") in OBSERVED and rec.get("seen_by") and set(rec["seen_by"]) <= set(covered):
            rec["state"] = "not-seen"
            changed += 1
        elif not rec.get("state"):
            rec["state"] = "not-installed"
    try:
        save(store, tools)
        if rows or obs:
            sd = os.path.join(store, "scans")
            os.makedirs(sd, exist_ok=True)
            with open(os.path.join(sd, "%s.jsonl" % stamp), "a", encoding="utf-8") as f:
                for r in rows + obs:
                    f.write(json.dumps({k: r[k] for k in ("source", "host", "kind", "name", "state", "id") if r.get(k)},
                                       ensure_ascii=False, sort_keys=True) + "\n")
            for old in sorted(glob.glob(os.path.join(sd, "*.jsonl")))[:-KEEP_SCANS]:
                os.remove(old)
    except OSError as e:
        result(error="store not writable: %s" % (e.strerror or e), store=store)
        return 1
    result(store=store, records=len(tools), seed_added=added_seed, created=created, observed=len(seen_now),
           state_changed=changed, sources_covered=sorted(covered), refused=refused)
    return 0


def _candidates(store, skill, need=None, exclude=()):
    own = load_registry(store)
    team = load_team(store)
    declined_team = {(norm(d.get("name")), d.get("skill")) for d in load_team_declined(store)}
    own_idx = index(own)
    order = {s["id"]: i for i, s in enumerate(load_seed())}      # the seed lists the likeliest tool first
    team_names = {norm(t.get("name")) for t in team}
    cands = [(t, "own") for t in own] + [(t, "team") for t in team if norm(t.get("name")) not in own_idx]
    out = []
    for t, origin in cands:
        skills = t.get("skills") if isinstance(t.get("skills"), list) else []
        if skill not in skills:
            continue
        if need and need not in (t.get("needs") or []):
            continue
        if t.get("id") in exclude:                          # the step already offers it in its own question
            continue
        if t.get("state") in ("installed", "connected") or t.get("verdict") == "deprecated":
            continue
        if any(isinstance(d, dict) and d.get("skill") == skill for d in t.get("declined") or []):
            continue
        if origin == "team" and (norm(t.get("name")), skill) in declined_team:
            continue
        via = own_idx.get(norm(t.get("via"))) if t.get("via") else None      # reached through another tool you have
        if via is not None and via.get("state") in ("installed", "connected"):
            continue
        rank = 0 if (origin == "own" and t.get("verdict") == "recommended") else \
            1 if origin == "team" or str(t.get("recommended_by", "")).startswith("team:") or \
            norm(t.get("name")) in team_names else \
            2 if "seed" in (t.get("sources") or []) else 3
        primary = skills.index(skill)                       # a tool that names the skill first serves it first
        out.append((rank, primary, order.get(t.get("id"), len(order)), norm(t.get("name")), t, origin))
    return sorted(out, key=lambda x: x[:4])


def _skill_ok(skill):
    if skill not in skill_names():
        result(error="not a skill of the plugin")
        return False
    return True


def cmd_suggest(args):
    if not _skill_ok(args.skill):
        return 2
    store = store_dir(args)
    if not os.path.isfile(os.path.join(store, "registry.json")) and not load_team(store):
        result(suggest=None, why="no registry")
        return 0
    try:
        c = _candidates(store, args.skill, args.need, tuple(x.strip() for x in (args.exclude or "").split(",") if x.strip()))
    except Unreadable:
        result(suggest=None, why="registry.json does not read")
        return 0
    if not c:
        result(suggest=None)
        return 0
    t, origin = c[0][4], c[0][5]
    tid = t.get("id") or cc.slugify(t.get("name"))
    print(json.dumps({"id": tid, "name": t.get("name"), "job": t.get("job", ""), "connect": t.get("connect", ""),
                      "state": t.get("state", "not-installed"), "origin": origin}, ensure_ascii=False, sort_keys=True))
    result(suggest=tid, origin=origin)
    return 0


def _find(tools, key):
    for t in tools:
        if t["id"] == key:
            return t
    return index(tools).get(norm(key))


def _team_match(store, key):
    return [t for t in load_team(store) if norm(t.get("name")) == norm(key) or cc.slugify(t.get("name")) == key]


def cmd_decline(args):
    if not _skill_ok(args.skill):
        return 2
    store = store_dir(args)
    try:
        tools = load_registry(store)
    except Unreadable as e:
        return _unreadable(str(e))
    rec = _find(tools, args.id)
    try:
        if rec is None:
            team = _team_match(store, args.id)
            if not team:
                result(error="no record with that id")
                return 2
            name = team[0].get("name")                 # a team record stays the team's: the «ні» is kept beside it
            kept = [d for d in load_team_declined(store)
                    if not (norm(d.get("name")) == norm(name) and d.get("skill") == args.skill)]
            if not args.undo:
                kept.append({"name": name, "skill": args.skill, "date": today()})
            _write(os.path.join(store, "team-declined.json"), json.dumps(kept, ensure_ascii=False, indent=1) + "\n")
            result(id=cc.slugify(name), skill=args.skill, declined=not args.undo, team=True)
            return 0
        if args.undo:
            rec["declined"] = [d for d in rec.get("declined") or [] if d.get("skill") != args.skill]
        elif not any(d.get("skill") == args.skill for d in rec.get("declined") or []):
            rec["declined"] = list(rec.get("declined") or []) + [{"skill": args.skill, "date": today()}]
        save(store, tools)
    except OSError as e:
        result(error="store not writable: %s" % (e.strerror or e))
        return 1
    result(id=rec["id"], skill=args.skill, declined=not args.undo)
    return 0


def _parse_fields(pairs):
    """(fields, bad) — `bad` names a field, never its value."""
    out, bad = {}, []
    skills = skill_names()
    for p in pairs or []:
        if "=" not in p:
            bad.append("(no =)")
            continue
        k, v = p.split("=", 1)
        k, v = k.strip(), v.strip()
        if k not in USER_FIELDS:
            bad.append("(unknown field)")
            continue
        if flagged(v):
            bad.append(k + " (refused: " + ",".join(flagged(v)) + ")")
            continue
        if k in LIST_FIELDS:
            vals = [x.strip() for x in v.split(",") if x.strip()]
            allowed = skills if k == "skills" else CONTOURS
            if [x for x in vals if x not in allowed]:
                bad.append(k)
                continue
            out[k] = vals
        elif k == "shared":
            out[k] = v.lower() in ("true", "yes", "1", "так")
        elif (k == "verdict" and v and v not in VERDICTS) or (k == "access" and v and v not in ACCESS) or \
                (k == "publishes" and v and v not in PUBLISHES):
            bad.append(k)
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
    for k, v in fields.items():
        if v in ("", []):
            rec.pop(k, None)
            rec["cleared"] = _add_unique(rec.get("cleared"), k)       # a seed never fills it back
        else:
            rec[k] = v
            rest = [c for c in rec.get("cleared") or [] if c != k]
            if rest:
                rec["cleared"] = rest
            else:
                rec.pop("cleared", None)
    try:
        save(store, tools)
    except OSError as e:
        result(error="store not writable: %s" % (e.strerror or e))
        return 1
    result(id=rec["id"], **{what: sorted(fields)})
    return 0


def cmd_add(args):
    store = store_dir(args)
    try:
        tools = load_registry(store)
    except Unreadable as e:
        return _unreadable(str(e))
    if args.from_team:
        team = _team_match(store, args.from_team)
        if not team:
            result(error="no team record with that name")
            return 2
        if _find(tools, team[0].get("name")):
            result(error="already in the registry", id=_find(tools, team[0].get("name"))["id"])
            return 2
        rec = _from_team(team[0], tools)
        tools.append(rec)
        return _apply(rec, {}, tools, store, "added")
    name = valid_name(args.name or "")
    if not name or args.kind not in KINDS:
        result(error="add needs a name (letters, digits, spaces, .-_@+:()/') and --kind (%s)" % "|".join(KINDS))
        return 2
    if args.state and args.source == "user":
        result(error="--state comes only with a search result (--source registry-search|catalog)")
        return 2
    if _find(tools, name):
        result(error="already in the registry", id=_find(tools, name)["id"])
        return 2
    fields, bad = _parse_fields(args.fields)
    if bad:
        result(error="unknown, invalid or refused fields", fields=bad)
        return 2
    rec = {"id": new_id(name, tools), "name": name, "kind": args.kind,
           "state": args.state or "not-installed", "sources": [args.source]}
    if args.state:
        rec["seen"] = today()
    tools.append(rec)
    return _apply(rec, fields, tools, store, "added")


def cmd_set(args):
    store = store_dir(args)
    try:
        tools = load_registry(store)
    except Unreadable as e:
        return _unreadable(str(e))
    rec = _find(tools, args.id)
    if rec is None:
        result(error="no record with that id")
        return 2
    fields, bad = _parse_fields(args.fields)
    if bad or not fields:
        result(error="unknown, invalid or refused fields", fields=bad or ["(none given)"])
        return 2
    return _apply(rec, fields, tools, store, "set")


def _context_text(args, home):
    """The user's context for the registrations: --context, else the home's own when --home was given (never the
    environment's then), else the usual search."""
    if getattr(args, "context", None):
        p = cc.find_context(args.context)
    elif args.home:
        p = os.path.join(home, ".grow-pm", "local-context.md")
        p = p if os.path.isfile(p) else None
    else:
        p = cc.find_context(None, home=home)
    return (_read_bounded(p) or "") if p else ""


def _team_record(r, skills):
    """A core's record as the registry may show it, or None — enums closed, lists of real skills, texts filtered."""
    name = valid_name(r.get("name"))
    if not name:
        return None
    rec = {"name": name}
    for k in ("job", "connect", "recommended_by", "checked"):
        v = r.get(k)
        if isinstance(v, str) and v.strip():
            if flagged(v):
                return None
            rec[k] = clean(v)
    for k, allowed in (("kind", KINDS), ("access", ACCESS), ("verdict", VERDICTS), ("publishes", PUBLISHES)):
        if r.get(k) in allowed:
            rec[k] = r[k]
    for k, allowed in (("skills", skills), ("contours", CONTOURS)):
        v = r.get(k)
        v = [v] if isinstance(v, str) else (v if isinstance(v, list) else [])
        v = [x for x in v if x in allowed]
        if v:
            rec[k] = v
    return rec


def _cores(args, home):
    import ctx_repos as cr
    import provider_bundle as pb
    skipped, out = [], []
    for repo in cr.load_repos(_context_text(args, home), home, skipped=skipped):
        root = repo.get("core_root")
        if not root or not os.path.isdir(root):
            continue
        m, _ = pb.read_manifest(root)
        if m is not None:
            out.append((repo, root, m))
    return out, skipped


def cmd_team(args):
    home, store = home_dir(args), store_dir(args)
    cores, skipped = _cores(args, home)
    skills = skill_names()
    read, why, dropped = {}, [], 0
    for repo, root, m in cores:
        if not m.s("tools_file"):
            continue
        path = os.path.realpath(os.path.join(root, str(m.s("tools_file"))))
        if not (path + os.sep).startswith(os.path.realpath(root) + os.sep) or not os.path.isfile(path):
            why.append({"core": repo["id"], "why": "tools_file outside the core or missing"})
            continue
        try:
            recs = cc.read_yaml_records(_read_bounded(path) or "", "tools")
        except ValueError as e:
            why.append({"core": repo["id"], "why": "tools_file does not read: %s" % str(e)[:120]})
            continue
        kept = []
        for r in recs:
            rec = _team_record(r, skills)
            if rec is None:
                dropped += 1
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
    gone, live = [], {cc.slugify(k) for k in read}
    for p in glob.glob(os.path.join(store, "team", "*.json")):     # a list no core publishes any more is no list
        if os.path.basename(p)[:-5] not in live:
            try:
                os.remove(p)
                gone.append(os.path.basename(p)[:-5])
            except OSError:
                pass
    try:
        _write(os.path.join(store, "tools.md"), render(load_registry(store), load_team(store)))
    except (OSError, Unreadable):
        pass
    result(team=read, skipped=why, dropped=dropped, removed=sorted(gone), registrations_skipped=len(skipped))
    return 0


def _yaml_scalar(v):
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, list):
        return "[" + ", ".join(json.dumps(str(x), ensure_ascii=False) for x in v) + "]"
    return json.dumps(str(v), ensure_ascii=False)


def cmd_export(args):
    store = store_dir(args)
    try:
        shared = [t for t in load_registry(store) if t.get("shared") is True]
    except Unreadable as e:
        return _unreadable(str(e))
    owners = []
    try:
        for repo, _, m in _cores(args, home_dir(args))[0]:
            owners.append({"core": repo["id"], "owner_label": clean(m.s("owner_label") or "", MAX_NAME)})
    except Exception:          # the owners are a courtesy line; a registration that does not read never stops the export
        pass
    keep, held = [], 0
    for t in shared:
        rec = {k: t[k] for k in EXPORT_FIELDS if t.get(k) not in (None, "", [])}
        if never(rec):
            held += 1
            continue
        keep.append(rec)
    if not keep:
        result(exported=0, file=None, held=held, cores=owners)
        return 0
    lines = ["# Tools shared from a Grow PM tools registry (references/tool-registry.md §5).",
             "# Put this file in the core and name its path in the provider manifest: tools_file: <path>.",
             "tools:"]
    for rec in sorted(keep, key=lambda x: norm(x.get("name"))):
        for i, k in enumerate(k for k in EXPORT_FIELDS if k in rec):
            lines.append(("  - " if i == 0 else "    ") + "%s: %s" % (k, _yaml_scalar(rec[k])))
    path = os.path.join(store, "export", "tools-shared-%s.yaml" % today())
    try:
        _write(path, "\n".join(lines) + "\n")
    except OSError as e:
        result(error="store not writable: %s" % (e.strerror or e))
        return 1
    result(exported=len(keep), file=path, held=held, cores=owners)
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(prog="tools_scan.py", description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd")

    def common(p):
        p.add_argument("--store", help="the registry folder (default ~/.grow-pm/knowledge-library/tools)")
        p.add_argument("--home", help="the home whose host files and context are read (default the user's); "
                                      "installed apps are always this machine's")
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
    p.add_argument("--need", help="what the step needs (a tag of the seed's `needs`), e.g. mind-map, transcript")
    p.add_argument("--exclude", help="ids the step already offers in its own question, comma-separated")
    p = common(sub.add_parser("decline"))
    p.add_argument("--skill", required=True)
    p.add_argument("--id", required=True)
    p.add_argument("--undo", action="store_true")
    p = common(sub.add_parser("add"))
    p.add_argument("--name")
    p.add_argument("--kind")
    p.add_argument("--from-team")
    p.add_argument("--source", choices=("user", "registry-search", "catalog"), default="user")
    p.add_argument("--state", choices=("connected", "not-installed"))
    p.add_argument("fields", nargs="*")
    p = common(sub.add_parser("set"))
    p.add_argument("--id", required=True)
    p.add_argument("fields", nargs="*")
    p = common(sub.add_parser("team"))
    p.add_argument("--context")
    p = common(sub.add_parser("export"))
    p.add_argument("--context")
    args = ap.parse_args(argv)
    fn = {"scan": cmd_scan, "merge": cmd_merge, "suggest": cmd_suggest, "decline": cmd_decline, "add": cmd_add,
          "set": cmd_set, "team": cmd_team, "export": cmd_export}.get(args.cmd)
    if fn is None:
        ap.print_help()
        return 2
    return fn(args)


if __name__ == "__main__":
    sys.exit(main())
