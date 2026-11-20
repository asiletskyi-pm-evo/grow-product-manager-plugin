#!/usr/bin/env python3
"""Grow PM — trusted endpoints: the engine reaches only the provider addresses you approved (since v4.9.1).

A provider registration (`{vault}/{plugin_folder}/_System/providers/<id>.yaml`, `~/.grow-pm/providers/<id>.yaml`;
references/context-provider-protocol.md §3b) names `endpoint.url` and, optionally, `endpoint.headers_env` — the
environment variable that holds a request header. Whoever can edit that file would decide where the engine sends your
header, your search queries and the names of your notes. So the file does not decide: the engine sends a request only
to the pair «address + variable name» you approved, kept in a file of yours outside every vault and outside the
registrations' folder (§13 «Trusted endpoints»).

- trust_file(home)       `<home>/.grow-pm/trust/providers.json` — schema `provider-trust/1`, mode 0600 in a 0700
                         folder: {schema, seeded_at, entries: [{id, url, headers_env, at, how}]}. `url` is the address
                         as `parse` normalises it (no credentials, no query); `headers_env` the variable's NAME or null —
                         a value is never stored; `how` is `seeded` (the first run) or `approved` (`ctx provider trust`).
- parse(url)             an `Address` (normal, origin, request_url) or None — `ctx_mcp.split_url` underneath
- load(home)             the file as a dict, None when there is none; `TrustError` when it cannot be read (a link, not
                         JSON, another schema) — such a file refuses everything and is never rewritten by a first run
- seed(home, repos, late, now)   the first run after the update (R37): when there is no trust file, every registration
                         with an address that may be reached is trusted — one line each, `Довірено наявну реєстрацію …`
                         — and the file keeps `seeded_at`; an empty list is a file too, so it happens once. A remote http
                         address is not trusted and is named; a registration still downloading (`late`) puts it off.
- verdict(repo, home)    None when the registration's pair is the one approved for its id, else an `Untrusted` (not
                         raised): its `why` — new · changed · transport · unreadable — and its `line` for the user
- client_for(repo, home, factory, **kw)   the one way to an MCP client (validate check 31): `Untrusted` is raised before
                         the factory is called, so no request, no header; else the factory gets the approved address and
                         the header `ctx_mcp.headers_from_env` reads from the variable
- approve(home, repo, now) · revoke(home, rid)   `ctx provider trust <id>` and `untrust <id>`
- check_protocol(root)   validate check 31

The trust home of a registration is the `Home` that `ctx_repos.load_repos` puts on it — a class no registration file
can produce (its own `_`-keys are dropped by `ctx_repos.normalise`) — or the home a caller passes. Stdlib only.
"""
import collections
import datetime
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ctx_common as cc  # noqa: E402
import ctx_mcp as cm  # noqa: E402
import ctx_store as cs  # noqa: E402

TRUST_REL = (".grow-pm", "trust", "providers.json")    # never under providers/ (read as registrations), never in a vault
SCHEMA = "provider-trust/1"
SEEDED, APPROVED = "seeded", "approved"
MAX_BYTES = 1024 * 1024
ID = re.compile(r"[a-z0-9][a-z0-9-]{0,63}\Z")           # an id a command line may carry as it is (§3b: kebab-case, ≤ 64)
VAR = re.compile(r"[A-Za-z_][A-Za-z0-9_]{0,127}\Z")     # a variable name, nothing a shell or a line would read otherwise
COMMAND = "ctx provider trust"
REASONS = {"new": "нова", "changed": "змінилась", "transport": "не https", "unreadable": "файл довіри не читається"}
NOTHING_SENT = "нічого не надіслано"


class Home(str):
    """A trust home set by the engine (`ctx_repos.load_repos`): a text no registration file can make."""


class TrustError(Exception):
    """The trust file cannot be read or written, or an approval that may not be given; the message is safe to print."""


class Untrusted(Exception):
    """A registration whose address may not be reached: `why` (a key of REASONS), `line` (what the user reads)."""

    def __init__(self, rid, why, line):
        super().__init__(line)
        self.rid, self.why, self.line = rid, why, line


Address = collections.namedtuple("Address", "normal origin request_url")


def trust_file(home):
    return os.path.join(home, *TRUST_REL)


def parse(url):
    """The address as the engine reads it, or None: `normal` (scheme://host[:port]/path — what is kept and matched),
    `origin` (scheme://host[:port] — what the lines show) and `request_url` (`normal` with its query: where the request
    goes; credentials and the fragment never travel)."""
    parts = cm.split_url(url)
    if parts is None:
        return None
    scheme, host, port, path, query = parts
    origin = "%s://%s%s" % (scheme, "[%s]" % host if ":" in host else host, ":%d" % port if port else "")
    return Address(origin + path, origin, origin + path + ("?" + query if query else ""))


def _safe(text, limit=80):
    return cc.clip(cc.CONTROLS.sub(" ", str(text or "")).strip(), limit)


def _shown(rid):
    """An id as a line shows it: as it is when kebab-case, else with every character a shell would read masked."""
    rid = str(rid or "")
    return rid if ID.match(rid) else re.sub(r"[^A-Za-z0-9._-]", "?", rid)[:64] or "?"


def _var_word(var):
    return "змінна %s" % var if var else "без змінної"


# ------------------------------------------------------------------ the file
def _check_links(home):
    path = trust_file(home)
    for p in (os.path.dirname(path), path):
        if os.path.islink(p):
            raise TrustError("%s — посилання, а не файл" % p)


def load(home):
    """The trust file as a dict ({schema, seeded_at, entries}), None when there is none. TrustError when it is a link (or
    sits in a folder that is one), larger than MAX_BYTES, not UTF-8 JSON, of another schema, or not of this shape."""
    path = trust_file(home)
    _check_links(home)
    if not os.path.lexists(path):
        return None
    try:
        with open(path, "rb") as f:
            raw = f.read(MAX_BYTES + 1)
    except OSError as e:
        raise TrustError("%s: %s" % (path, e.strerror or type(e).__name__))
    if len(raw) > MAX_BYTES:
        raise TrustError("%s: більше %d байтів" % (path, MAX_BYTES))
    try:
        data = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, ValueError, RecursionError):
        raise TrustError("%s: не JSON" % path)
    if not isinstance(data, dict) or data.get("schema") != SCHEMA or not isinstance(data.get("entries"), list):
        raise TrustError("%s: незнайома схема (чекаю %s)" % (path, SCHEMA))
    if not all(isinstance(e, dict) and isinstance(e.get("id"), str) and isinstance(e.get("url"), str)
               and (e.get("headers_env") is None or isinstance(e.get("headers_env"), str)) for e in data["entries"]):
        raise TrustError("%s: запис без id, адреси чи з дивною змінною" % path)
    return data


def _write(home, data, exclusive=False):
    """Write the trust file: 0600 in a 0700 folder, under the ctx guard, through a temp file — `os.replace`, or with
    `exclusive` a hard link that fails when the file appeared meanwhile (another run seeded it): then False."""
    path = trust_file(home)
    folder = os.path.dirname(path)
    cs.check_target(path)
    _check_links(home)
    os.makedirs(folder, mode=0o700, exist_ok=True)
    os.chmod(folder, 0o700)
    tmp = "%s.%d.tmp" % (path, os.getpid())
    if os.path.lexists(tmp):
        os.unlink(tmp)
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0), 0o600)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            f.write("\n")
            f.flush()
            os.fsync(f.fileno())
        if not exclusive:
            os.replace(tmp, path)
            return True
        try:
            os.link(tmp, path)
            return True
        except FileExistsError:
            return False
        except OSError:                                 # a file system with no hard links: the narrow window stays
            if os.path.lexists(path):
                return False
            os.replace(tmp, path)
            return True
    finally:
        if os.path.lexists(tmp):
            os.unlink(tmp)


def _day(now):
    return str(now or datetime.datetime.now().astimezone().isoformat(timespec="seconds"))[:10]


def _entry(rid, address, var, now, how):
    return {"id": rid, "url": address.normal, "headers_env": var or None, "at": _day(now), "how": how}


# ------------------------------------------------------------------ the first run (R37)
def seed(home, repos, late=(), now=None):
    """The first run after the update: lines to print (see the module's doc). Nothing when the trust file is there —
    readable or not, a link or not. `late` lists registrations not read in time (still downloading): the run is put off
    with one line, so a registration iCloud has not brought down is not shut out of it. A home that cannot be written
    (a read-only sandbox, the guard) is one line: no file, nothing trusted."""
    path = trust_file(home)
    if os.path.lexists(path) or os.path.islink(os.path.dirname(path)):
        return []
    if late:
        return ["довіру адресам ще не встановлено: реєстрація ще завантажується (%s) — до наступного запуску %s"
                % (_safe(os.path.basename(late[0])), NOTHING_SENT)]
    entries, lines = [], []
    for repo in repos or ():
        rid, ep = repo.get("id") or "", repo.get("endpoint") or {}
        if not ep.get("url"):
            continue
        address, var = parse(ep["url"]), ep.get("headers_env") or ""
        problem = _problem(rid, ep["url"], var)
        if problem:
            lines.append("Не довірено %s: %s" % (_shown(rid), problem))
            continue
        entries.append(_entry(rid, address, var, now, SEEDED))
        lines.append("Довірено наявну реєстрацію %s: %s (%s)" % (rid, address.origin, _var_word(var)))
    stamp = now or datetime.datetime.now().astimezone().isoformat(timespec="seconds")
    try:
        if not _write(home, {"schema": SCHEMA, "seeded_at": stamp, "entries": entries}, exclusive=True):
            return []                                   # another run seeded it meanwhile: its lines were its own
    except (OSError, cs.PathRefused, TrustError) as e:
        why = e.strerror if isinstance(e, OSError) and e.strerror else str(e) or type(e).__name__
        return ["файл довіри не створено (%s) — жодну адресу не схвалено, %s" % (_safe(why, 200), NOTHING_SENT)]
    return lines


def _problem(rid, url, var):
    """Why a registration's pair may never be approved as it stands, or "": an id a command line cannot carry, an address
    that is not plainly one or is http to another computer, a variable name that is not plain."""
    if not ID.match(rid or ""):
        return "id реєстрації не kebab-case — таку не схвалюю"
    address = parse(url)
    if address is None:
        return "адреса не читається"
    if cm.transport_problem(url):
        return "не https: %s — http лише до цього комп'ютера (127.0.0.1, ::1, localhost)" % address.origin
    if var and not VAR.match(var):
        return "назва змінної не проста — таку не схвалюю"
    return ""


# ------------------------------------------------------------------ the verdict
def _home_of(repo, home):
    if home:
        return home
    h = repo.get("_trust_home")
    return h if isinstance(h, Home) else None


def _refusal(rid, why, detail, hint=True):
    tail = ". Схвалити: %s %s" % (COMMAND, rid) if hint and ID.match(rid or "") else ""
    return Untrusted(rid, why, "%s: адресу не схвалено (%s) — %s%s" % (_shown(rid), detail, NOTHING_SENT, tail))


def verdict(repo, home=None):
    """None when the registration's address and variable are the pair approved for its id; else an Untrusted (see the
    module's doc). A registration with no address is refused too: there is nothing to approve."""
    rid = repo.get("id") or ""
    ep = repo.get("endpoint") or {}
    url, var = ep.get("url") or "", ep.get("headers_env") or ""
    if not url:
        return _refusal(rid, "transport", "нема адреси", hint=False)
    problem = _problem(rid, url, var)
    if problem:
        return _refusal(rid, "transport", problem, hint=False)
    address = parse(url)
    where = _home_of(repo, home)
    if not where:
        return _refusal(rid, "new", REASONS["new"])
    try:
        data = load(where)
    except TrustError as e:
        return _refusal(rid, "unreadable", "%s: %s" % (REASONS["unreadable"], _safe(e, 200)), hint=False)
    entry = next((e for e in (data or {}).get("entries") or () if e.get("id") == rid), None)
    if entry is None:
        return _refusal(rid, "new", REASONS["new"])
    if entry.get("url") == address.normal and (entry.get("headers_env") or None) == (var or None):
        return None
    was = parse(entry.get("url") or "")
    if was is None or was.origin != address.origin:
        change = "%s → %s" % (was.origin if was else "?", address.origin)
    elif was.normal != address.normal:
        change = "%s → %s" % (was.normal, address.normal)
    else:
        old = entry.get("headers_env") or ""
        change = "%s → %s" % (_var_word(old if VAR.match(old) else "?" if old else ""), _var_word(var))
    return _refusal(rid, "changed", "%s: %s" % (REASONS["changed"], change))


def client_for(repo, home=None, factory=None, **kw):
    """The client for an approved registration — `factory(request_url, headers=…, **kw)`, `ctx_mcp.McpClient` by default —
    or Untrusted, raised before the factory is called and before the variable is read."""
    refused = verdict(repo, home)
    if refused is not None:
        raise refused
    ep = repo["endpoint"]
    headers = cm.headers_from_env(ep["headers_env"]) if ep.get("headers_env") else {}
    return (factory or cm.McpClient)(parse(ep["url"]).request_url, headers=headers, **kw)


# ------------------------------------------------------------------ ctx provider trust | untrust
def approve(home, repo, now=None):
    """Approve what the registration says now: its id, its address (normalised) and its variable's name — the entry
    that replaces the id's. TrustError: no address, a pair that may never be approved (`_problem`), no trust file yet
    (the first run has not happened: an approval now would shut it out), or a file that cannot be read."""
    rid = repo.get("id") or ""
    ep = repo.get("endpoint") or {}
    url, var = ep.get("url") or "", ep.get("headers_env") or ""
    if not url:
        raise TrustError("у реєстрації %s немає адреси — схвалювати нічого" % _shown(rid))
    problem = _problem(rid, url, var)
    if problem:
        raise TrustError("%s: %s" % (_shown(rid), problem))
    data = load(home)
    if data is None:
        raise TrustError("файлу довіри ще немає (%s) — перший запуск ще не відбувся" % trust_file(home))
    entry = _entry(rid, parse(url), var, now, APPROVED)
    data["entries"] = [e for e in data["entries"] if e.get("id") != rid] + [entry]
    _write(home, data)
    return entry


def revoke(home, rid):
    """Remove the id's entry; how many were removed (0: none was there). TrustError: no file, or one that cannot be read."""
    data = load(home)
    if data is None:
        raise TrustError("файлу довіри немає (%s)" % trust_file(home))
    kept = [e for e in data["entries"] if e.get("id") != rid]
    gone = len(data["entries"]) - len(kept)
    if gone:
        data["entries"] = kept
        _write(home, data)
    return gone
