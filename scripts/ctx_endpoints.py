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
                         a value is never stored; `how` is `approved` (`ctx provider trust`) — `seeded`, which a first run of v4.9.1–
                         v4.12.3 wrote, approves nothing since v4.12.4.
- parse(url)             an `Address` (normal, origin, request_url) or None — `ctx_mcp.split_url` underneath
- load(home)             the file as a dict, None when there is none; `TrustError` when it cannot be read (a link, not
                         JSON, another schema) — such a file refuses everything and is never rewritten by a first run
- seed(home, repos, late, now)   the first run: when there is no trust file it is created empty (`seeded_at` kept) —
                         since v4.12.4 no registration is trusted by itself (R37 withdrawn, the audit of 2026-11-26),
                         one line, `довіра адресам: жодну наявну реєстрацію не довірено автоматично …`
- verdict(repo, home)    None when the registration's pair is the one the user approved for its id (`how: approved`),
                         else an `Untrusted` (not raised): its `why` — new · changed · seeded · transport · unreadable —
                         and its `line` for the user; an entry an earlier first run wrote (`how: seeded`) is no approval
- client_for(repo, home, factory, **kw)   the one way to an MCP client (validate check 31): `Untrusted` is raised before
                         the factory is called, so no request, no header; else the factory gets the approved address and
                         the header `ctx_mcp.headers_from_env` reads from the variable
- approve(home, repo, now) · revoke(home, rid)   `ctx provider trust <id>` and `untrust <id>`
- check_protocol(root)   validate check 31

The trust home of a registration is the `Home` that `ctx_repos.load_repos` puts on it — a class no registration file
can produce (its own `_`-keys are dropped by `ctx_repos.normalise`) — or the home a caller passes. Stdlib only.
"""
import collections
import contextlib
import datetime
import hashlib
import json
import os
import re
import sys
import time
import urllib.parse

try:
    import fcntl
except ImportError:                                     # not POSIX: approve and revoke go without the lock
    fcntl = None

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
REASONS = {"new": "нова", "changed": "змінилась", "transport": "не https", "unreadable": "файл довіри не читається",
           "unseeded": "файлу довіри ще немає", "seeded": "довірено без твого схвалення"}
FIRST_RUN = ("довіра адресам: жодну наявну реєстрацію не довірено автоматично — кожну адресу схвалиш сам, одним "
             "питанням (%s <id>)")
SEED_MARK = (".grow-pm", ".trust-seeded")               # the first run happened in this home — outside trust/, which may go
LINE_MAX = 300                                          # a refusal line, its «Схвалити: …» tail included (callers clip at 300)
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


Address = collections.namedtuple("Address", "normal origin request_url query_sha shown")
LOCK_WAIT_S = 10.0


def trust_file(home):
    return os.path.join(home, *TRUST_REL)


def parse(url):
    """The address as the engine reads it, or None: `normal` (scheme://host[:port]/path — what is kept and matched),
    `origin` (scheme://host[:port] — what the lines show), `request_url` (`normal` with its query: where the request
    goes; credentials and the fragment never travel), `query_sha` (the sha256 of the query, matched with the rest since
    review 1 — a gateway may route by it; None for none) and `shown` (`normal` with every character of the path outside
    letters, digits and `/._~-` percent-encoded: a registration's text never reaches a line as it is)."""
    parts = cm.split_url(url)
    if parts is None:
        return None
    scheme, host, port, path, query = parts
    origin = "%s://%s%s" % (scheme, "[%s]" % host if ":" in host else host, ":%d" % port if port else "")
    return Address(origin + path, origin, origin + path + ("?" + query if query else ""),
                   hashlib.sha256(query.encode("utf-8")).hexdigest() if query else None,
                   origin + urllib.parse.quote(path, safe="/._~-"))


def shown(url):
    """An endpoint as a line or a result may show it: the address parsed (`Address.shown`), else "" — never the text as
    written (review 1 #1: the netloc as written and the host connected to may differ)."""
    address = parse(url)
    return address.shown if address else ""


def _safe(text, limit=80):
    return cc.clip(cc.CONTROLS.sub(" ", str(text or "")).strip(), limit)


def _shown(rid):
    """An id as a line shows it: as it is when kebab-case, else with every character a shell would read masked."""
    rid = str(rid or "")
    return rid if ID.match(rid) else re.sub(r"[^A-Za-z0-9._-]", "?", rid)[:64] or "?"


def _var_word(var):
    return "змінна %s" % var if var else "без змінної"


def var_shown(var):
    """A variable as a line shows it, with the header it gives — its NAME, never its value (review of the branch #7: any
    variable holding `Name: value` becomes a header): `змінна X → заголовок Y` · `змінна X (заголовка не дає: <why>)` ·
    `без змінної` · `змінна з непростою назвою` (not repeated)."""
    if not var:
        return "без змінної"
    if not VAR.match(var):
        return "змінна з непростою назвою"
    got = cm.headers_from_env(var)
    if got:
        return "змінна %s → заголовок %s" % (var, next(iter(got)))
    return "змінна %s (заголовка не дає: %s)" % (var, _safe(cm.header_problem(var), 120))


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
               and (e.get("headers_env") is None or isinstance(e.get("headers_env"), str))
               and (e.get("query_sha256") is None or isinstance(e.get("query_sha256"), str)) for e in data["entries"]):
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
    return {"id": rid, "url": address.normal, "query_sha256": address.query_sha, "headers_env": var or None,
            "at": _day(now), "how": how}


def _query_word(address):
    return ", з параметрами запиту" if address.query_sha else ""


def code_of(repo):
    """The code of the pair a registration says now (since review 1): `ctx provider trust <id>` shows it with the pair,
    and only `--code <it>` approves — so a registration switched between the question and the yes is never approved.
    "" for a pair that cannot be approved."""
    rid = repo.get("id") or ""
    ep = repo.get("endpoint") or {}
    url, var = ep.get("url") or "", ep.get("headers_env") or ""
    if not url or _problem(rid, url, var):
        return ""
    address = parse(url)
    return hashlib.sha256("\n".join((rid, address.normal, address.query_sha or "", var)).encode("utf-8")).hexdigest()[:12]


def lock_file(home):
    return os.path.join(os.path.dirname(trust_file(home)), ".lock")


@contextlib.contextmanager
def _locked(home):
    """The trust file's lock (since review 1 #5): approve and revoke read and write under it, so a change between the
    read and the write of another is never undone. Busy for LOCK_WAIT_S → TrustError. Without fcntl (not POSIX): no lock."""
    _check_links(home)
    path = lock_file(home)
    cs.check_target(path)
    os.makedirs(os.path.dirname(path), mode=0o700, exist_ok=True)
    fd = os.open(path, os.O_RDWR | os.O_CREAT | getattr(os, "O_NOFOLLOW", 0), 0o600)
    try:
        if fcntl is not None:
            until = time.monotonic() + LOCK_WAIT_S
            while True:
                try:
                    fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    break
                except BlockingIOError:
                    if time.monotonic() > until:
                        raise TrustError("файл довіри зайнятий іншим процесом — спробуй ще раз")
                    time.sleep(0.05)
        yield
    finally:
        os.close(fd)                                    # closing releases the lock


# ------------------------------------------------------------------ the first run (R37 withdrawn in v4.12.4)
def seed(home, repos, late=(), now=None):
    """The first run: lines to print (see the module's doc). Since v4.12.4 (the audit of 2026-11-26, R37 withdrawn) it
    trusts nothing: when there is no trust file it is created empty, whatever registrations are there — a registration
    lies in a vault that syncs, so one planted there before the first run would otherwise get your queries and your
    header. Each address is approved by the user, one question each (`ctx provider trust <id>` → `--code`). One line
    when some registration has an address. Nothing when the trust file is there — readable or not, a link or not. A home
    that cannot be written (a read-only sandbox, the guard) is one line: no file, nothing approved. `late` (a
    registration still downloading) no longer matters: nothing is trusted from what is there, so nothing waits for it."""
    path = trust_file(home)
    if os.path.lexists(path) or os.path.islink(os.path.dirname(path)):
        return []
    addressed = any((r.get("endpoint") or {}).get("url") for r in repos or ())
    stamp = now or datetime.datetime.now().astimezone().isoformat(timespec="seconds")
    try:
        if not _write(home, {"schema": SCHEMA, "seeded_at": stamp, "entries": []}, exclusive=True):
            return []                                   # another run created it meanwhile
    except (OSError, cs.PathRefused, TrustError) as e:
        if not addressed:                               # review of the branch #4: nothing to say on every skill start
            return []
        why = e.strerror if isinstance(e, OSError) and e.strerror else str(e) or type(e).__name__
        return ["файл довіри не створено (%s) — жодну адресу не схвалено, %s" % (_safe(why, 200), NOTHING_SENT)]
    _mark(home, stamp)
    return [FIRST_RUN % COMMAND] if addressed else []


def _mark(home, stamp):
    """The mark that the first run happened in this home, beside the trust folder: a trust file that goes later (deleted,
    a backup restored without it) comes back empty, never seeded again. A mark that cannot be written costs only that."""
    mark = os.path.join(home, *SEED_MARK)
    try:
        cs.check_target(mark)
        fd = os.open(mark, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0), 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(stamp + "\n")
    except (OSError, cs.PathRefused):
        pass


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


def _refusal(rid, why, detail, hint=True, after=""):
    """The line: at most LINE_MAX characters with its tail whole — the detail is cut to fit (review of the branch #5:
    a caller's clip at 300 must never take the «Схвалити: …» a skill asks by)."""
    tail = ". Схвалити: %s %s" % (COMMAND, rid) if hint and ID.match(rid or "") else after
    head = "%s: адресу не схвалено (" % _shown(rid)
    rest = ") — %s%s" % (NOTHING_SENT, tail)
    detail = cc.clip(detail, max(20, LINE_MAX - len(head) - len(rest)))
    return Untrusted(rid, why, head + detail + rest)


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
    new = "%s: %s" % (REASONS["new"], address.origin)
    if not where:
        return _refusal(rid, "new", new)
    try:
        data = load(where)
    except TrustError as e:
        return _refusal(rid, "unreadable", "%s: %s" % (REASONS["unreadable"], _safe(e, 200)), hint=False)
    if data is None:                                    # review of the branch #3: no approval can succeed here yet
        return _refusal(rid, "unseeded", REASONS["unseeded"], hint=False,
                        after="; схвалиш там, де ctx може писати в ~/.grow-pm (%s %s)" % (COMMAND, rid)
                        if ID.match(rid or "") else "")
    entry = next((e for e in data.get("entries") or () if e.get("id") == rid), None)
    if entry is None:
        return _refusal(rid, "new", new)
    if entry.get("how") != APPROVED:                    # since v4.12.4: an entry a first run wrote (v4.9.1–v4.12.3) is
        return _refusal(rid, "seeded", "%s: %s" % (REASONS["seeded"], address.origin))   # no approval of yours
    if (entry.get("url") == address.normal and (entry.get("query_sha256") or None) == address.query_sha
            and (entry.get("headers_env") or None) == (var or None)):
        return None
    was = parse(entry.get("url") or "")
    if was is None or was.origin != address.origin:
        change = "%s → %s" % (was.origin if was else "?", address.origin)
    elif was.normal != address.normal:
        change = "%s → %s" % (was.shown, address.shown)
    elif (entry.get("query_sha256") or None) != address.query_sha:
        change = "параметри запиту %s" % ("з'явились" if not entry.get("query_sha256") else
                                          "прибрано" if not address.query_sha else "інші")
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
def approve(home, repo, now=None, code=None):
    """Approve what the registration says now: its id, its address (normalised, its query as a hash) and its variable's
    name — the entry that replaces the id's, written under the lock. `code` (the CLI always passes one): the pair's
    `code_of` as shown to the user; another → TrustError, nothing written. TrustError also: no address, a pair that may
    never be approved (`_problem`), no trust file yet (the first run has not happened: an approval now would shut it
    out), a file that cannot be read, the lock busy."""
    rid = repo.get("id") or ""
    ep = repo.get("endpoint") or {}
    url, var = ep.get("url") or "", ep.get("headers_env") or ""
    if not url:
        raise TrustError("у реєстрації %s немає адреси — схвалювати нічого" % _shown(rid))
    problem = _problem(rid, url, var)
    if problem:
        raise TrustError("%s: %s" % (_shown(rid), problem))
    if code is not None and code != code_of(repo):
        raise TrustError("код %s не збігається з тим, що реєстрація %s каже зараз — нічого не схвалено; покажи її ще раз: "
                         "%s %s" % (_safe(code, 20), _shown(rid), COMMAND, _shown(rid)))
    if not os.path.lexists(trust_file(home)):
        raise TrustError("файлу довіри ще немає (%s) — перший запуск ще не відбувся" % trust_file(home))
    with _locked(home):
        data = load(home)
        if data is None:
            raise TrustError("файлу довіри ще немає (%s) — перший запуск ще не відбувся" % trust_file(home))
        entry = _entry(rid, parse(url), var, now, APPROVED)
        data["entries"] = [e for e in data["entries"] if e.get("id") != rid] + [entry]
        _write(home, data)
    return entry


def revoke(home, rid):
    """Remove the id's entry under the lock; how many were removed (0: none was there). TrustError: no file, one that
    cannot be read, the lock busy."""
    if not os.path.lexists(trust_file(home)):
        raise TrustError("файлу довіри немає (%s)" % trust_file(home))
    with _locked(home):
        data = load(home)
        if data is None:
            raise TrustError("файлу довіри немає (%s)" % trust_file(home))
        kept = [e for e in data["entries"] if e.get("id") != rid]
        gone = len(data["entries"]) - len(kept)
        if gone:
            data["entries"] = kept
            _write(home, data)
    return gone


# ------------------------------------------------------------------ validate check 31
PROTOCOL = "references/context-provider-protocol.md"
ALLOWED_CLIENT_FILES = ("ctx_mcp.py", "ctx_endpoints.py")       # where the client class and the header reader may be named
WORDS = ("жодну наявну реєстрацію не довірено автоматично", "адресу не схвалено", NOTHING_SENT, "ctx provider trust <id>", "--code <code>",
         "ctx provider trust --list", "ctx provider untrust <id>", "~/.grow-pm/trust/providers.json", SCHEMA)


def _read(root, rel):
    try:
        with open(os.path.join(root, rel), encoding="utf-8") as f:
            return f.read()
    except OSError:
        return None


def _code(text):
    """Python source without comments and string literals that span lines (docstrings): what names a class in code."""
    text = re.sub(r'(?s)("""|\'\'\').*?\1', '""', text)
    return "\n".join(line.split("#", 1)[0] for line in text.splitlines())


def check_protocol(root):
    """Validate check 31 (since v4.9.1): [problems], each naming its file. (1) No script outside ALLOWED_CLIENT_FILES
    names the MCP client class or calls `headers_from_env` — `client_for` stays the one way to a client and a header.
    (2) The trust file's path is under `.grow-pm/`, not in the registrations' folder, and not built from a vault or the
    storage root. (3) §13 of the provider protocol names what the code has: the reasons' words, the commands (and the
    parser defines them), the loopback hosts, the first-run, refusal and shadow lines, the file and its schema."""
    errs = []
    sdir = os.path.join(root, "scripts")
    for name in sorted(os.listdir(sdir)) if os.path.isdir(sdir) else ():
        if not name.endswith(".py") or name in ALLOWED_CLIENT_FILES:
            continue
        code = _code(_read(root, os.path.join("scripts", name)) or "")
        if re.search(r"\bMcpClient\b", code):
            errs.append("scripts/%s names the MCP client class — build a client only through ctx_endpoints.client_for" % name)
        if re.search(r"\bheaders_from_env\s*\(", code):
            errs.append("scripts/%s reads a header with headers_from_env — only ctx_endpoints.client_for may" % name)
        if re.search(r"\b_parse_env\b", code):
            errs.append("scripts/%s calls ctx_mcp._parse_env, which gives the header's raw value" % name)
        if name != "ctx_mcp.py" and re.search(r"^\s*(import\s+(urllib\.request|http\.client|socket|requests)\b|from\s+"
                                              r"(urllib\.request|urllib\s+import\s+request|http\.client|http\s+import\s+client|"
                                              r"socket|requests)\b)", code, re.M):
            errs.append("scripts/%s imports a way to the network — requests go only through ctx_mcp, by client_for" % name)
        if any(re.search(r"os\.environ|getenv", line) and "headers_env" in line for line in code.splitlines()):
            errs.append("scripts/%s reads the variable endpoint.headers_env names from the environment itself" % name)
    me = _code(_read(root, "scripts/ctx_endpoints.py") or "")
    rel = re.search(r"TRUST_REL\s*=\s*\(([^)]*)\)", me)
    parts = re.findall(r'"([^"]*)"', rel.group(1)) if rel else []
    if not parts or parts[0] != ".grow-pm" or "providers" in parts[:-1] or not parts[-1].endswith(".json"):
        errs.append("scripts/ctx_endpoints.py: TRUST_REL must be under .grow-pm/, outside providers/ (read as registrations): %s"
                    % (parts or "not found"))
    body = re.search(r"def trust_file\(home\):\n(.*?)\n(?=\S|\Z)", me, re.S)
    if not body or re.search(r"storage_root|vault_entries|plugin_folder|vault", body.group(1)) or "home" not in body.group(1):
        errs.append("scripts/ctx_endpoints.py: trust_file must be the home's .grow-pm path, never a vault or the storage root")
    proto = _read(root, PROTOCOL) or ""
    m = re.search(r"^## 13\. Trusted endpoints.*?(?=^## |\Z)", proto, re.S | re.M)
    sec = m.group(0) if m else ""
    if not sec:
        errs.append("%s: no «## 13. Trusted endpoints» section" % os.path.basename(PROTOCOL))
    for key, words in sorted(REASONS.items()):
        if not re.search(r"\| `%s` \| `%s[`:]" % (re.escape(key), re.escape(words)), sec):
            errs.append("%s §13: the reason `%s` with its words «%s» is not in the table" % (os.path.basename(PROTOCOL), key, words))
    for w in WORDS:
        if sec and w not in sec:
            errs.append("%s §13 does not name «%s»" % (os.path.basename(PROTOCOL), w))
    mcp = _code(_read(root, "scripts/ctx_mcp.py") or "")
    hosts = re.search(r"LOOPBACK\s*=\s*\(([^)]*)\)", mcp)
    hosts = re.findall(r'"([^"]*)"', hosts.group(1)) if hosts else []
    named = set(re.findall(r"`(127\.0\.0\.1|::1|localhost|[0-9.:]+)`", re.search(r"\*\*The transport\.\*\*.*", sec).group(0))) \
        if "**The transport.**" in sec else set()
    if not hosts or set(hosts) != named:
        errs.append("ctx_mcp.py LOOPBACK %s ≠ the hosts §13 «The transport» names %s" % (sorted(hosts), sorted(named)))
    common = _read(root, "scripts/ctx_common.py") or ""
    shadow = re.search(r'SHADOWED = "реєстрація %s: ([^"]+)"', common)
    if not shadow or "реєстрація <id>: %s" % shadow.group(1) not in sec:
        errs.append("ctx_common.py SHADOWED and the line §13 «A private registration wins» names differ")
    # since v4.12.4 (the audit of 2026-11-26, finding 2): no address is trusted without the user — the first run writes
    # no entry, an entry is written only as `approved`, and the verdict passes only an approved one
    seed_body = re.search(r"def seed\(.*?(?=\ndef )", me, re.S)
    if not seed_body or re.search(r"_entry\(|entries\.append|SEEDED", seed_body.group(0)):
        errs.append("scripts/ctx_endpoints.py: the first run trusts a registration by itself — it must create the trust file "
                    "empty; each address is approved by the user (ctx provider trust <id> --code)")
    if re.search(r'^[^"\n]*\b_entry\([^\n]*\bSEEDED\b', me, re.M):
        errs.append("scripts/ctx_endpoints.py: an entry is written as `seeded` — only `approved` (ctx provider trust)")
    verd = re.search(r"def verdict\(.*?(?=\ndef )", me, re.S)
    if not verd or not re.search(r'entry\.get\("how"\) != APPROVED', verd.group(0)):
        errs.append("scripts/ctx_endpoints.py: verdict passes an entry that is not `approved` — an entry an earlier first run "
                    "seeded is no approval of the user's")
    first = re.search(r'FIRST_RUN = \("([^"]*)"', me)
    if not first or "жодну наявну реєстрацію не довірено автоматично" not in first.group(1):
        errs.append("scripts/ctx_endpoints.py: the first-run line is not «довіра адресам: жодну наявну реєстрацію не довірено "
                    "автоматично …» as §13 names it")
    parser = _read(root, "scripts/ctx.py") or ""
    for cmd in ("trust", "untrust"):
        if 'pp.add_parser("%s"' % cmd not in parser:
            errs.append("scripts/ctx.py: no `provider %s` in the parser, while §13 names it" % cmd)
    return errs
