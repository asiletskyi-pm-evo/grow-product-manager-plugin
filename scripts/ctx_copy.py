#!/usr/bin/env python3
"""Grow PM — the plugin's own copy of a repository that lives only on an MCP server (since v3.24.0).

A registration with an endpoint and no folder of its own (no `core_root`, no `paths`) can be copied into
`~/.grow-pm/cores/<id>/`: every note under `endpoint.root`, at its path under that root, so the copy is laid out as
the core folder would be. Once a pass has completed, `ctx_repos.load_repos` takes the copy as the repository's
`core_root` (`attach`), and blocks, the team block, the index, search, entities and bridges read it as a folder.
references/context-provider-protocol.md §12.12.

One pass (`run`) is the prom_sync pattern, generalised:
  * a lock of the copy (`.ctx-copy/lock`; a live one younger than LOCK_STALE_S → "busy"), the handshake (none →
    "unreachable", nothing written), one `vault_list_by_folder(root)`;
  * the guard against an incomplete index: an empty listing, or one below MIN_RATIO of the last complete one →
    "held": not one note written, not one moved;
  * every note fetched (WORKERS threads, each its own client on the same allow-list) and decided on its own:
    same (nothing written) · new · updated (the old file into `.backup/<stamp>/` first) · kept (changed here, not on
    the server: stays) · conflict (changed on both: yours stays, the server's goes to `~/.grow-pm/conflicts/<id>/`) ·
    failed (did not arrive: the file stays as it was);
  * complete when the guard passed and failed ≤ max(FAILED_FLOOR, 1 %) — else "partial": writes stand, nothing moves;
  * a note gone from the server is moved (never deleted) into `.removed/<day>/` only after two complete listings in a
    row without it, at least REMOVE_AFTER_S apart; it can come back with `restore`.

Nothing outside the copy, its conflicts folder (and, from the daily sync, the day's report part) is ever written:
`check_folder` refuses a folder that is not the plugin's (exit 4) and every write passes `ctx_store.check_target`
under a guard of those two roots. The copy is not in `ctx undo` — it is a cache of the server (protocol §12.12).
Stdlib only.
"""
import concurrent.futures
import datetime
import hashlib
import json
import os
import re
import shutil
import sys
import threading
import time
import unicodedata

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ctx_common as cc  # noqa: E402
import ctx_mcp as cm  # noqa: E402
import ctx_store as cs  # noqa: E402
import ctx_wrappers as cw  # noqa: E402

SCHEMA = "context-copy/1"
MIN_RATIO = 0.5                   # a listing below half of the last complete one is an incomplete index: held
WORKERS = 12
SAVE_EVERY = 500                  # the state is written every this many notes, so a pass that was cut resumes
LOCK_STALE_S = 15 * 60
BACKUP_DAYS = 30
REMOVE_AFTER_S = 20 * 3600        # two complete listings without a note, at least this far apart, move it
FAILED_FLOOR = 5                  # complete: failed ≤ max(FAILED_FLOOR, 1 % of the listing)
DUE_S = 24 * 3600                 # the daily pass: a complete pass older than this…
RETRY_S = 3600                    # …and no attempt within this
SERVICE = ".ctx-copy"
BACKUP = ".backup"
REMOVED = ".removed"
LIST_TOOL, NOTE_TOOL = "vault_list_by_folder", "vault_get_note"
OUTCOMES = ("complete", "partial", "held", "unreachable", "busy")
MAX_LISTED = 20                   # paths named in a result (failed, conflicts, removed)

N = lambda s: unicodedata.normalize("NFC", s or "")   # noqa: E731


class CopyError(Exception):
    """A copy that cannot be made here: a folder that is not the plugin's, a busy lock (exit 4)."""


class Busy(CopyError):
    """Another pass holds the copy's lock."""


class Refused(CopyError):
    """A folder the plugin may not write (check_folder)."""


# ------------------------------------------------------------------ places
def cores_dir(home):
    return os.path.join(home, ".grow-pm", "cores")


def copy_dir(home, rid):
    return os.path.join(cores_dir(home), rid)


def conflicts_dir(home, rid):
    return os.path.join(home, ".grow-pm", "conflicts", rid)


def state_path(folder):
    return os.path.join(folder, SERVICE, "state.json")


SAFE_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,80}\Z")


def check_folder(home, rid, regs=()):
    """The copy folder of `rid`, or CopyError (nothing written) when it is not one the plugin may write: an id that is no
    plain name; a folder (or `cores/` itself) that is a symbolic link or leads outside `~/.grow-pm/cores/`; a folder that
    exists, is not empty and has no `.ctx-copy/state.json` (someone else's); a folder inside the paths or the core folder
    of any registration (`regs`, normalised or raw) — so the copy never writes where another tool writes."""
    if not isinstance(rid, str) or not SAFE_ID.match(rid) or rid in (".", ".."):
        raise Refused("the repository id %r is not a plain name — no copy folder for it" % rid)
    base, folder = cores_dir(home), copy_dir(home, rid)
    for p in (os.path.join(home, ".grow-pm"), base, folder):
        if os.path.islink(p):
            raise Refused("%s is a symbolic link — the copy writes only into a real folder" % p)
    real_base = os.path.realpath(base)
    real = os.path.realpath(folder)
    if not (real == os.path.join(real_base, rid)):
        raise Refused("%s leads outside %s" % (folder, base))
    if os.path.isdir(folder) and os.listdir(folder) and not os.path.isfile(state_path(folder)):
        raise Refused("%s is not empty and is not a copy of the plugin (no %s/state.json) — nothing written"
                        % (folder, SERVICE))
    for r in regs:
        roots = [p for p in list(r.get("paths") or []) + [r.get("core_root") if r.get("core_from") != "copy" else ""] if p]
        if roots and cc.is_under(folder, roots):
            raise Refused("%s lies inside the folder of the registration %s — nothing written" % (folder, r.get("id")))
    return folder


# ------------------------------------------------------------------ paths
CONTROL = re.compile(r"[\x00-\x1f\x7f  ]")


def rel_of(server_path, root, writable=()):
    """(the path under the copy, "") for a note the copy takes, or (None, why not): not text; outside `root`; not `.md`;
    absolute, with `..`, `\\`, a control character, an empty part or a part that starts with a dot (`.obsidian/`);
    under the registration's `writable` globs (someone's own layer). The path is NFC."""
    if not isinstance(server_path, str) or not server_path:
        return None, "no path"
    p = N(server_path)
    root = N(root or "")
    if root and not p.startswith(root):
        return None, "outside the root"
    rel = p[len(root):]
    if not rel.lower().endswith(".md"):
        return None, "not a note"
    if rel.startswith("/") or "\\" in rel or CONTROL.search(rel) or re.match(r"[A-Za-z]:", rel):
        return None, "not a relative path"
    parts = rel.split("/")
    if any(x in ("", ".", "..") or x.startswith(".") for x in parts):
        return None, "a hidden or relative part"
    if writable and cc._writable(rel, list(writable)):
        return None, "a writable path of the registration"
    return rel, ""


def fold(rel):
    """The key two spellings of one name share on a case- and normalisation-insensitive disk (APFS)."""
    return N(rel).casefold()


# ------------------------------------------------------------------ frontmatter and hashes
def canon_fm(fm):
    return json.dumps(fm or {}, ensure_ascii=False, sort_keys=True, default=str)


def sha1(text):
    return hashlib.sha1(text.encode("utf-8")).hexdigest()


def server_hash(fm, content):
    """The semantic hash of a note as the server gave it: its frontmatter (canonical JSON) and its text (NFC, no
    trailing blanks) — prom_sync's, so a change on the server shows whatever YAML the copy wrote."""
    return sha1(canon_fm(fm) + "\n␞\n" + N(content or "").rstrip())


RESERVED = {"true", "false", "yes", "no", "on", "off", "null", "none", "~", "y", "n"}
NUMBER = re.compile(r"[-+]?(\.?\d[\d_]*(\.\d*)?|\d[\d_]*\.)([eE][-+]?\d+)?\Z|[-+]?\.(inf|nan)\Z|0[xXoObB][0-9a-fA-F_]+\Z", re.I)
DATE = re.compile(r"\d{4}-\d{1,2}-\d{1,2}")
PLAIN_START = re.compile(r"[^\s\-?:,\[\]{}#&*!|>'\"%@`]")


def _plain_ok(s):
    """Can `s` be written as a plain YAML scalar that every reader of the plugin (`ctx_index`, `provider_bundle.fget`,
    `ctx_common.read_yaml_subset`), PyYAML and Obsidian read back as this same text?"""
    return bool(s) and s == s.strip() and s.isprintable() and PLAIN_START.match(s) is not None \
        and ": " not in s and " #" not in s and not s.endswith(":") and not s.endswith('"') \
        and s.lower() not in RESERVED and not NUMBER.match(s) and not DATE.match(s)


def scalar(v):
    """One value as YAML text: a plain scalar when that is safe, else JSON in double quotes (valid YAML)."""
    if v is None:
        return ""
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, int):
        return str(v)
    if isinstance(v, float):
        return repr(v) if v == v and v not in (float("inf"), float("-inf")) else json.dumps(str(v))
    s = v if isinstance(v, str) else str(v)
    return s if _plain_ok(s) else json.dumps(s, ensure_ascii=False)


PLAIN_KEY = re.compile(r"[^\s:#\-?\[\]{},&*!|>'\"%@`][^:#\n]*\Z")


def _key(k):
    """A key as YAML text: plain unless it carries a character of YAML's structure (a reserved word such as `off` stays
    plain: the plugin's readers and YAML 1.2 read it as text), else JSON in double quotes."""
    k = str(k)
    return k if PLAIN_KEY.match(k) and k == k.strip() and k.isprintable() else json.dumps(k, ensure_ascii=False)


def dump_frontmatter(fm):
    """The frontmatter as a canonical YAML subset, keys in the server's order, every key on one line: a scalar; a list
    or a mapping as JSON flow (valid YAML; `["a", "b"]` is the kit's own form of a list, which `ctx_index` and
    `provider_bundle.fget` read — a block list would make `fget` read the next line); None as `""`."""
    lines = []
    for k, v in fm.items():
        key = _key(k)
        if isinstance(v, (list, dict)):
            lines.append("%s: %s" % (key, json.dumps(v, ensure_ascii=False, default=str)))
        else:
            lines.append("%s: %s" % (key, scalar(v) if v is not None else '""'))
    return "\n".join(lines)


def render(fm, content):
    """The file the copy writes for a note: `---`, the frontmatter, `---`, the text (with a final newline). A text that
    already opens with its own frontmatter and comes with none apart (a server that serves the file whole) is written as
    it is."""
    content = content or ""
    body = content if content.endswith("\n") else content + "\n"
    if not (isinstance(fm, dict) and fm) and (content.startswith("---\n") or content.startswith("---\r\n")):
        return body
    if isinstance(fm, dict) and fm:
        return "---\n" + dump_frontmatter(fm) + "\n---\n" + body
    return body


# ------------------------------------------------------------------ state
def empty_state(rid, root):
    return {"schema": SCHEMA, "repo": rid, "root": root, "complete_at": "", "complete_listed": 0, "attempt_at": "",
            "outcome": "", "reason": "", "held_in_row": 0, "checked_at": "", "notes": {}, "last": {}}


def load_state(folder):
    """The copy's state, or None when the folder holds none. One that cannot be read raises CopyError: a copy whose
    state is lost is not overwritten as if it were new."""
    p = state_path(folder)
    if not os.path.isfile(p):
        return None
    try:
        with open(p, encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError, UnicodeDecodeError) as e:
        raise CopyError("the copy's state %s cannot be read (%s) — nothing written; move the folder aside to start over"
                        % (p, type(e).__name__))
    if not isinstance(data, dict) or data.get("schema") != SCHEMA or not isinstance(data.get("notes"), dict):
        raise CopyError("the copy's state %s is not %s — nothing written" % (p, SCHEMA))
    return data


def save_state(folder, state):
    cs.atomic_write(state_path(folder), json.dumps(state, ensure_ascii=False, sort_keys=True, indent=1) + "\n")


def copy_info(home, rid):
    """(folder, state) of a copy that has completed a pass, else (None, None) — never raises: a read for the
    registrations (`ctx_repos.load_repos`) must not fail over a copy."""
    folder = copy_dir(home, rid)
    try:
        if os.path.islink(folder) or not SAFE_ID.match(rid or ""):
            return None, None
        st = load_state(folder)
    except Exception:  # noqa: BLE001
        return None, None
    if not st or not st.get("complete_at"):
        return None, None
    return folder, st


def attach(repo, home):
    """`repo` (normalised) with its copy as the core folder when it has none of its own: a registration with no
    `core_root` and no `paths`, an endpoint url, and a copy that completed a pass → core_root = the copy, core_from
    "copy", copy_at = the day of that pass. A registration with a folder of its own never takes a copy."""
    if repo.get("core_root") or repo.get("paths") or not (repo.get("endpoint") or {}).get("url"):
        return repo
    folder, st = copy_info(home, repo.get("id") or "")
    if folder is None:
        return repo
    out = dict(repo)
    out.update({"core_root": folder, "core_from": "copy", "copy_at": st["complete_at"][:10]})
    return out


# ------------------------------------------------------------------ lock
def _alive(pid):
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except (OSError, ValueError, TypeError):
        return False


def _lock_body(path):
    try:
        with open(path, encoding="utf-8") as f:
            raw = f.read()
        held = json.loads(raw)
        return raw, int(held.get("pid")), float(held.get("at"))
    except (OSError, ValueError, TypeError, AttributeError):
        return None, None, 0.0


def take_lock(folder, now_s=None):
    """The copy's lock, or Busy. A pass refreshes it as it saves its state (`touch_lock`), so a lock of a live process is
    busy while it is younger than LOCK_STALE_S; an older one (a pass that hangs) and one of a process that is gone are
    taken over — by moving that very lock aside first, so two passes taking over at once never remove each other's."""
    p = os.path.join(folder, SERVICE, "lock")
    os.makedirs(os.path.dirname(p), exist_ok=True)
    cs.check_target(p)
    token = hashlib.sha1(("%s-%s-%s" % (os.getpid(), time.time(), id(p))).encode()).hexdigest()[:16]
    for _ in range(3):
        try:
            fd = os.open(p, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
            with os.fdopen(fd, "w") as f:
                f.write(json.dumps({"pid": os.getpid(), "at": time.time() if now_s is None else now_s, "token": token}))
            return p
        except FileExistsError:
            raw, pid, at = _lock_body(p)
            if pid is not None and _alive(pid) and time.time() - at < LOCK_STALE_S:
                raise Busy("another pass is copying %s (process %s) — try again later" % (os.path.basename(folder), pid))
            aside = "%s.stale-%s" % (p, token)
            try:
                os.rename(p, aside)                     # the lock file of a pass that is gone (a service file, not a note)
            except FileNotFoundError:
                continue
            if _lock_body(aside)[0] != raw:             # another pass took it over meanwhile: its lock goes back
                try:
                    os.link(aside, p)
                except OSError:
                    pass
                os.unlink(aside)
                raise Busy("another pass took over the lock of %s" % os.path.basename(folder))
            os.unlink(aside)
    raise Busy("the copy's lock could not be taken")


def _ours(path):
    raw, pid, _ = _lock_body(path)
    return pid == os.getpid() and raw is not None


def touch_lock(path):
    """The lock's time moved to now — only when it is still this process's."""
    raw, pid, _ = _lock_body(path)
    if pid != os.getpid():
        return
    held = json.loads(raw)
    held["at"] = time.time()
    try:
        cs.atomic_write(path, json.dumps(held))
    except OSError:
        pass


def release_lock(path):
    """The lock removed — only when it is still this process's (a lock another pass took over stays)."""
    if not _ours(path):
        return
    try:
        os.unlink(path)
    except OSError:
        pass


# ------------------------------------------------------------------ times
def stamp(now):
    return now.isoformat(timespec="seconds")


def parse(iso):
    try:
        t = datetime.datetime.fromisoformat(iso)
    except (TypeError, ValueError):
        return None
    return t if t.tzinfo else t.astimezone()


def due(state, now):
    """Is the daily pass due for this copy? Its last complete pass is DUE_S old or more, and no attempt was made within
    RETRY_S (or the last attempt is the complete pass itself). A copy with no complete pass is never due: the first copy
    is made by the user's command, not in the background."""
    if not state or not state.get("complete_at"):
        return False
    done = parse(state["complete_at"])
    if done is None:
        return False
    if (done - now).total_seconds() > DUE_S:            # a time more than a day ahead (another Mac's clock): unknown, due
        return True
    tried = parse(state.get("attempt_at") or "") or done
    if (tried - now).total_seconds() > DUE_S:
        tried = done
    return (now - done).total_seconds() >= DUE_S and (tried <= done or (now - tried).total_seconds() >= RETRY_S)


def lock_busy(folder):
    """Does a live pass hold the copy's lock now (as `take_lock` would judge it)? Reads only."""
    _, pid, at = _lock_body(os.path.join(folder, SERVICE, "lock"))
    return pid is not None and _alive(pid) and time.time() - at < LOCK_STALE_S


def background_choice(home, repo, now):
    """What the daily sync does about the copy of `repo` (normalised; the copy attached): None — it has no copy, or the
    registration has no `sync: daily` or is paused; else "busy" (a pass holds the lock), "not-due" or "due". Reads the
    copy's state only: no network, no lock."""
    if repo.get("core_from") != "copy" or repo.get("sync") != "daily" or repo.get("status") == "paused":
        return None
    folder, st = copy_info(home, repo["id"])
    if folder is None:
        return None
    if lock_busy(folder):
        return "busy"
    return "due" if due(st, now) else "not-due"


# ------------------------------------------------------------------ one file
def _file_facts(path):
    try:
        st = os.stat(path)
    except OSError:
        return None
    return st.st_mtime, st.st_size


def _file_sha(path):
    with open(path, "rb") as f:
        return hashlib.sha1(f.read()).hexdigest()


def local_changed(path, entry):
    """Was the file changed since the copy wrote it? (mtime, size) as written: no; else the sha of its bytes decides."""
    facts = _file_facts(path)
    if facts is None:
        return None                                   # not there
    if entry.get("mtime") == facts[0] and entry.get("size") == facts[1]:
        return False
    return _file_sha(path) != entry.get("local")


def decide(entry, srv, path, text):
    """The decision for one note that arrived: same · new · updated · kept · conflict (see the module's doc), or
    "adopt" — a file that is already the server's text although the state does not say so (a pass cut between its write
    and the state's save, or a conflict you settled by taking the server's version): counted as same, its row refreshed.
    `entry` is the state's row (None for a note the state does not know), `srv` the server hash, `text` the file it
    would write."""
    if entry is None or not entry.get("local"):
        if not os.path.lexists(path):
            return "new"
        return "adopt" if os.path.isfile(path) and _file_sha(path) == sha1(text) else "conflict"
    changed = local_changed(path, entry)
    if changed is None:
        return "new"
    if changed and _file_sha(path) == sha1(text):
        return "adopt"
    if entry.get("srv") == srv:
        return "kept" if changed else "same"
    return "conflict" if changed else "updated"


# ------------------------------------------------------------------ the pass
class Pass:
    """One pass of a copy (see `run`)."""

    def __init__(self, home, repo, now, client_factory=cm.McpClient, progress=None, workers=WORKERS):
        self.home, self.repo, self.now = home, repo, now
        self.rid = repo["id"]
        self.folder = copy_dir(home, self.rid)
        self.conflicts = conflicts_dir(home, self.rid)
        self.factory = client_factory
        self.progress = progress
        self.workers = workers
        self.day = now.date().isoformat()
        self.counts = dict.fromkeys(("new", "updated", "same", "kept", "conflict", "failed", "removed", "skipped"), 0)
        self.failed, self.conflict_paths, self.removed, self.skipped = [], [], [], []
        self.backup = None
        self.wrappers = {}                              # rel → (fm, content) of the wrappers that arrived this pass

    # -- helpers
    def _client(self):
        ep = self.repo["endpoint"]
        hdrs = cm.headers_from_env(ep["headers_env"]) if ep.get("headers_env") else {}
        return self.factory(ep["url"], headers=hdrs)

    def _write(self, rel, text):
        cs.atomic_write(os.path.join(self.folder, rel), text)

    def _backup(self, rel):
        if self.backup is None:
            self.backup = os.path.join(self.folder, BACKUP, self.now.strftime("%Y%m%d-%H%M%S"))
        dst = os.path.join(self.backup, rel)
        cs.check_target(dst)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copy2(os.path.join(self.folder, rel), dst)

    def _move_removed(self, rel):
        src = os.path.join(self.folder, rel)
        if not os.path.isfile(src):
            return False
        dst = os.path.join(self.folder, REMOVED, self.day, rel)
        n = 1
        while os.path.exists(dst):
            n += 1
            dst = os.path.join(self.folder, REMOVED, self.day, "%s (%d)%s" % (os.path.splitext(rel)[0], n, os.path.splitext(rel)[1]))
        cs.check_target(src)
        cs.check_target(dst)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        os.replace(src, dst)                            # moved, never deleted
        return True

    def _prune_backups(self):
        """`.backup/<stamp>/` folders older than BACKUP_DAYS — the copy's own backups, not anyone's notes."""
        base = os.path.join(self.folder, BACKUP)
        try:
            names = os.listdir(base)
        except OSError:
            return
        limit = (self.now - datetime.timedelta(days=BACKUP_DAYS)).strftime("%Y%m%d-%H%M%S")
        for name in names:
            if re.fullmatch(r"\d{8}-\d{6}", name) and name < limit and not os.path.islink(os.path.join(base, name)):
                cs.check_target(os.path.join(base, name))
                shutil.rmtree(os.path.join(base, name), ignore_errors=True)

    def _fetch(self, local, path):
        """(fm, content) of one note, or raises — in a worker thread, with that thread's own client."""
        c = getattr(local, "client", None)
        if c is None:
            c = local.client = self._client()
        note = c.call(NOTE_TOOL, {"path": path})
        content = note.get("content")
        if not isinstance(content, str):
            why = note.get("error")
            raise cm.McpError(why if isinstance(why, str) and why.strip() else "the note has no text content")
        fm = note.get("frontmatter")
        return (fm if isinstance(fm, dict) else {}), content

    # -- the run
    def run(self, regs=()):
        check_folder(self.home, self.rid, regs)
        with cs.guard_roots([self.folder, self.conflicts]):
            os.makedirs(os.path.join(self.folder, SERVICE), exist_ok=True)
            self.lock = take_lock(self.folder)
            try:
                return self._run()
            finally:
                release_lock(self.lock)

    def _result(self, state, outcome, reason, listed, started):
        state.update({"attempt_at": stamp(self.now), "outcome": outcome, "reason": reason, "checked_at": stamp(self.now)})
        if outcome == "held":
            state["held_in_row"] = int(state.get("held_in_row") or 0) + 1
        elif outcome in ("complete", "partial"):
            state["held_in_row"] = 0
        state["last"] = dict(self.counts, listed=listed)
        save_state(self.folder, state)
        return {"outcome": outcome, "reason": reason, "counts": dict(self.counts), "listed": listed,
                "last_complete_listed": state.get("complete_listed") or 0, "failed": self.failed[:MAX_LISTED],
                "conflicts": self.conflict_paths[:MAX_LISTED], "removed": self.removed[:MAX_LISTED],
                "folder": self.folder, "backup": self.backup, "elapsed_s": round(time.monotonic() - started, 1),
                "complete_at": state.get("complete_at") or "", "held_in_row": state.get("held_in_row") or 0}

    def _run(self):
        started = time.monotonic()
        state = load_state(self.folder) or empty_state(self.rid, self.repo["endpoint"]["root"])
        root = self.repo["endpoint"]["root"]
        self._prune_backups()
        state["attempt_at"] = stamp(self.now)           # a pass that is cut counts as an attempt (retried in RETRY_S)
        save_state(self.folder, state)
        client = self._client()
        if not client.probe():
            return self._result(state, "unreachable", cc.clip(getattr(client, "last_error", "") or "no answer", 300), 0, started)
        try:
            items = client.call_list(LIST_TOOL, {"folder": root})
        except cm.McpError as e:
            return self._result(state, "unreachable", cc.clip("%s: %s" % (LIST_TOOL, e), 300), 0, started)
        listed, seen = [], {}
        for it in items:
            rel, why = rel_of(it.get("path"), root, self.repo.get("writable") or ())
            if rel is None:
                self.counts["skipped"] += 1
                continue
            key = fold(rel)
            if key in seen:
                self.counts["skipped"] += 1
                self.skipped.append(rel)
                continue
            seen[key] = rel
            listed.append((rel, N(it["path"])))
        last = int(state.get("complete_listed") or 0)
        if not listed or (last and len(listed) < MIN_RATIO * last):
            why = ("the server listed no notes under %r" % root if not listed else
                   "the server listed %d notes, under half of the last complete listing (%d) — an incomplete index"
                   % (len(listed), last))
            return self._result(state, "held", why, len(listed), started)
        notes = state["notes"]
        for rel, _ in listed:                           # back on the server before it was moved: no longer missing
            if rel in notes:
                notes[rel].pop("missing_since", None)
        done = 0
        local = threading.local()
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.workers) as pool:
            futures = {pool.submit(self._fetch, local, path): rel for rel, path in listed}
            for fut in concurrent.futures.as_completed(futures):
                rel = futures[fut]
                try:
                    fm, content = fut.result()
                except Exception as e:  # noqa: BLE001 — one note that did not come is a count, never the pass
                    self.counts["failed"] += 1
                    self.failed.append(rel)
                    continue
                self._one(notes, rel, fm, content)
                done += 1
                if done % SAVE_EVERY == 0:
                    save_state(self.folder, state)
                    touch_lock(self.lock)
                    if self.progress:
                        self.progress("копія: %d з %d…" % (done, len(listed)))
        complete = self.counts["failed"] <= max(FAILED_FLOOR, len(listed) // 100)
        if complete:
            self._missing(notes, {rel for rel, _ in listed})
        self._unpack(state)
        if complete:
            state.update({"complete_at": stamp(self.now), "complete_listed": len(listed)})
        why = "" if complete else "%d notes did not arrive — over the limit of a complete pass" % self.counts["failed"]
        return self._result(state, "complete" if complete else "partial", why, len(listed), started)

    def _one(self, notes, rel, fm, content):
        if cw.is_wrapper(fm):
            self.wrappers[rel] = (fm, content)
        srv = server_hash(fm, content)
        text = render(fm, content)
        path = os.path.join(self.folder, rel)
        entry = notes.get(rel)
        try:
            what = decide(entry, srv, path, text)
            if what in ("new", "updated"):
                if what == "updated":
                    self._backup(rel)
                self._write(rel, text)
                facts = _file_facts(path)
                notes[rel] = {"srv": srv, "local": sha1(text), "mtime": facts[0], "size": facts[1]}
            elif what in ("same", "adopt"):
                facts = _file_facts(path)
                row = dict(entry or {}, srv=srv)
                if what == "adopt" or not row.get("local"):
                    row["local"] = sha1(text)
                row["mtime"], row["size"] = facts
                row.pop("restored", None)
                notes[rel] = row
                what = "same"
            elif what == "conflict":
                cs.atomic_write(os.path.join(self.conflicts, self.day, rel), text)
                self.conflict_paths.append(rel)
                row = dict(entry or {}, srv=srv)
                if not row.get("local"):                # a file the state did not know is yours: never taken as written
                    row.update({"local": sha1(text), "mtime": None, "size": None})
                notes[rel] = row
            else:                                       # kept: yours stays, the server's is as it was
                notes[rel] = dict(entry, srv=srv)
        except (OSError, UnicodeError, cs.PathRefused):  # one file that cannot be written is one failed note
            what = "failed"
            self.failed.append(rel)
        self.counts[what] += 1

    def _unpack(self, state):
        """The wrappers of this pass (ctx_wrappers) unpacked beside them — the manifest first, so that the basename of its
        `bundles_file` may be unpacked too. A file is written only when it differs. A wrapper that does not unpack, and one
        the state no longer knows (moved into `.removed/`), leaves no file: one unpacked before is moved into
        `.removed/` (never left stale, never deleted); `wrappers` keeps the reason (`wrapper_problem`). A wrapper that did
        not arrive this pass leaves its file as it is."""
        unpacked = state.setdefault("unpacked", {})       # target → the wrapper's rel
        faults = state.setdefault("wrappers", {})          # wrapper rel → {"file", "why"}
        manifest = None
        order = sorted(self.wrappers, key=lambda r: (str(self.wrappers[r][0].get("file") or "").strip() != cw.MANIFEST, r))
        for rel in order:
            fm, content = self.wrappers[rel]
            body = content
            if content.startswith("---\n"):                  # a server that serves the note whole
                body = re.sub(r"\A---\n.*?\n---\n?", "", content, count=1, flags=re.S)
            name, text, why = cw.unwrap(fm, body, cw.allowed_names(manifest))
            target = "/".join([x for x in rel.split("/")[:-1]] + [name]) if name and not why else ""
            if why:
                faults[rel] = {"file": name, "why": why}
                for t, src in list(unpacked.items()):
                    if src == rel:
                        self._drop_unpacked(unpacked, t)
                continue
            faults.pop(rel, None)
            for t, src in list(unpacked.items()):           # the wrapper now names another file: the old one goes
                if src == rel and t != target:
                    self._drop_unpacked(unpacked, t)
            path = os.path.join(self.folder, target)
            try:
                current = open(path, encoding="utf-8", newline="").read() if os.path.isfile(path) else None
            except (OSError, UnicodeDecodeError):
                current = None
            if current != text:
                cs.atomic_write(path, text)
            unpacked[target] = rel
            if name == cw.MANIFEST:
                try:
                    manifest = cc.read_yaml_subset(text)
                except ValueError:
                    manifest = None
        for t, src in list(unpacked.items()):               # a wrapper the state no longer knows: its file goes too
            if src not in state["notes"]:
                faults.pop(src, None)
                self._drop_unpacked(unpacked, t)
        for rel in list(faults):
            if rel not in state["notes"]:
                faults.pop(rel)

    def _drop_unpacked(self, unpacked, target):
        self._move_removed(target)
        unpacked.pop(target, None)

    def _missing(self, notes, present):
        """After a complete listing: a note the state knows and the listing does not is missing since now; one missing
        since an earlier complete listing at least REMOVE_AFTER_S ago is moved into `.removed/<day>/`. A restored note
        (not on the server, yours) is never moved."""
        folded = {fold(r) for r in present}
        for rel in sorted(notes):
            if rel in present:
                continue
            if fold(rel) in folded:                       # the same file under another spelling (a case-only rename)
                del notes[rel]
                continue
            row = notes[rel]
            if row.get("restored"):
                continue
            since = parse(row.get("missing_since") or "")
            if since is None:
                row["missing_since"] = stamp(self.now)
                continue
            if (self.now - since).total_seconds() < REMOVE_AFTER_S:
                continue
            try:
                moved = self._move_removed(rel)
            except (OSError, cs.PathRefused):            # left where it is; tried again after the next complete listing
                continue
            if moved or not os.path.exists(os.path.join(self.folder, rel)):
                del notes[rel]
                self.counts["removed"] += 1
                self.removed.append(rel)


def run(home, repo, now, client_factory=cm.McpClient, regs=(), progress=None, workers=WORKERS):
    """One pass of the copy of `repo` (normalised; an endpoint url) at `now` (an aware datetime) → the result
    (see Pass._result). CopyError / Busy when the folder may not be written or another pass holds it."""
    return Pass(home, repo, now, client_factory, progress, workers).run(regs)


def _versions(base, rel):
    """[(day, n, path)] of every version of `rel` in `.removed/` — `rel` itself and the `<name> (n).<ext>` a second move
    on one day gives it."""
    stem, ext = os.path.splitext(rel)
    rx = re.compile(re.escape(os.path.basename(stem)) + r"(?: \((\d+)\))?" + re.escape(ext) + r"\Z")
    out = []
    for day in (os.listdir(base) if os.path.isdir(base) else []):
        d = os.path.join(base, day, os.path.dirname(rel))
        for name in (os.listdir(d) if os.path.isdir(d) else []):
            mo = rx.match(name)
            if mo and os.path.isfile(os.path.join(d, name)):
                out.append((day, int(mo.group(1) or 1), os.path.join(d, name)))
    return sorted(out)


def restore(home, rid, rel, now, regs=()):
    """The newest version of `rel` in `.removed/` back into the copy; the state marks it restored (never moved again).
    → the path restored from. Refused when the folder may not be written, Busy under another pass, CopyError when there
    is no such version or a file is already at `rel`."""
    folder = check_folder(home, rid, regs)
    rel = N(rel).replace(os.sep, "/").lstrip("/")
    ok, why = rel_of(rel, "", ())
    if ok is None:
        raise CopyError("%s: %s" % (rel, why))
    with cs.guard_roots([folder]):
        lock = take_lock(folder)
        try:
            state = load_state(folder)                  # under the lock: a pass that ends meanwhile is not overwritten
            if state is None:
                raise CopyError("no copy of %s" % rid)
            found = _versions(os.path.join(folder, REMOVED), rel)
            if not found:
                raise CopyError("%s is not in %s/" % (rel, REMOVED))
            dst = os.path.join(folder, rel)
            if os.path.lexists(dst):
                raise CopyError("%s is already in the copy — nothing restored" % rel)
            src = found[-1][2]
            try:
                cs.check_target(src)
            except cs.PathRefused as e:
                raise Refused(str(e))
            cs.check_target(dst)
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            os.replace(src, dst)
            facts = _file_facts(dst)
            state["notes"][rel] = {"srv": None, "local": _file_sha(dst), "mtime": facts[0], "size": facts[1],
                                   "restored": now.date().isoformat()}
            save_state(folder, state)
        finally:
            release_lock(lock)
    return src


def wrapper_problem(state):
    """Why a wrapper of the copy did not unpack, in one line ("обгортка <file> не розгорнулась: <why>"), or "" when none
    failed — the team block's reason (ctx_repos)."""
    for rel, row in sorted(((state or {}).get("wrappers") or {}).items()):
        if isinstance(row, dict) and row.get("why"):
            return "обгортка %s не розгорнулась: %s" % (row.get("file") or rel, row["why"])
    return ""


def local_only(state):
    """How many notes of the copy are yours alone: restored from `.removed/`."""
    return sum(1 for r in (state or {}).get("notes", {}).values() if r.get("restored"))
