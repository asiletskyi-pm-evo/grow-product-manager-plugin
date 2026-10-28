#!/usr/bin/env python3
"""Grow PM — the context store's model (since v3.11.0).

The user's local-context.md is cut into section records that together cover every byte
exactly once, so compiling the records gives the file back byte for byte. Semantics:
references/context-protocol.md. Used by ctx_ops.py and the `ctx` command line.

- split_sections / assign_ids   the split rules and stable record ids
- render_record / parse_record  the record file: frontmatter + the section text as is
- compile_records               the compiled local-context.md
- read_text                     a read with a time budget (an iCloud-evicted file blocks until it downloads);
                                read_bytes the same for a file that need not be text
- atomic_write                  a write through a hidden temp file; remove_stale_tmp clears what a cut write left

Stdlib only.
"""
import contextlib
import hashlib
import json
import os
import re
import stat
import sys
import threading
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ctx_common as cc  # noqa: E402

# A `##` heading that starts with one of these is a `setting` record; any other is `custom`.
SETTING_TITLES = ("Judgment", "CJM Configuration", "Knowledge Library", "Templates", "Obsidian Vaults", "People",
                  "Planning", "Focus", "Release", "Terminology & Style", "Landscape", "Experiments", "Feedback",
                  "Custom Sections")
RECORD_KEYS = ("ctx", "id", "type", "title", "parent", "order", "owner", "source", "modified", "sha")


def sha_text(s):
    return hashlib.sha256((s or "").encode("utf-8")).hexdigest()


def _h2_type(title):
    if title == "User Profile":
        return "profile"
    if title == "Onboarding Status":
        return "onboarding"
    if title.startswith("Organization:"):
        return "org"
    if title.startswith(SETTING_TITLES):
        return "setting"
    return "custom"


def split_sections(text):
    """Fragments {type, title, heading, parent_index, text} in file order; their texts concatenate to `text`.

    A `## ` line starts a fragment; inside `## Organization:` so does `### Product: ` / `### Team: `.
    Lines inside fenced code and inside managed regions never split — except that a region whose
    begin marker is followed, after blank lines only, by a `## ` heading starts a fragment itself."""
    lines = text.splitlines(keepends=True)
    starts, pos = [], 0
    for ln in lines:
        starts.append(pos)
        pos += len(ln)
    spans = cc.managed_spans(text)
    begins = {a for a, _ in spans}

    def inside(off):
        return any(a < off < b for a, b in spans)

    cuts, fence, org_open = [], False, False
    for i, ln in enumerate(lines):
        s = ln.rstrip("\r\n")
        off = starts[i]
        if inside(off):
            continue
        if s.lstrip().startswith("```"):
            fence = not fence
            continue
        if fence:
            continue
        if s.startswith("## "):
            title = s[3:].strip()
            cuts.append((i, "h2", title, s))
            org_open = title.startswith("Organization:")
        elif org_open and (s.startswith("### Product: ") or s.startswith("### Team: ")):
            cuts.append((i, "h3", s[4:].strip(), s))
        elif off in begins:
            j = i + 1
            while j < len(lines) and not lines[j].strip():
                j += 1
            if j < len(lines) and lines[j].startswith("## "):
                head = lines[j].rstrip("\r\n")
                title = head[3:].strip()
                cuts.append((i, "h2", title, head))
                org_open = title.startswith("Organization:")

    frags = []
    first = cuts[0][0] if cuts else len(lines)
    if first > 0:
        head = next((l.rstrip("\r\n").lstrip("﻿") for l in lines[:first] if l.lstrip("﻿").startswith("# ")), "")
        frags.append(dict(type="header", title=head[2:].strip() if head else "header", heading=head or None,
                          parent_index=None, text="".join(lines[:first])))
    org_index = None
    for k, (i, kind, title, head) in enumerate(cuts):
        end = cuts[k + 1][0] if k + 1 < len(cuts) else len(lines)
        if kind == "h2":
            typ, parent = _h2_type(title), None
            org_index = len(frags) if typ == "org" else None
        else:
            typ, parent = ("product" if title.startswith("Product:") else "team"), org_index
        frags.append(dict(type=typ, title=title, heading=head, parent_index=parent, text="".join(lines[i:end])))
    return frags


def assign_ids(frags, taken=frozenset()):
    """Add `id`, `parent` (id or None) and `order` (10, 20, …) to each fragment."""
    used, out = set(taken), []
    for k, f in enumerate(frags):
        typ = f["type"]
        if typ in ("header", "profile", "onboarding"):
            base = typ
        else:
            name = f["title"]
            for pre in ("Organization:", "Product:", "Team:"):
                if name.startswith(pre):
                    name = name[len(pre):].strip()
                    break
            base = typ + "." + cc.slugify(name)
        rid, n = base, 2
        while rid in used:
            rid, n = "%s-%d" % (base, n), n + 1
        used.add(rid)
        pi = f.get("parent_index")
        out.append(dict(f, id=rid, order=(k + 1) * 10, parent=out[pi]["id"] if pi is not None else None))
    return out


OPTIONAL_KEYS = ("status", "verified", "ttl_days", "archived", "archived_reason", "former_after", "trashed", "read_by")
_FLOW_READ_BY = re.compile(r"^(read_by:[ \t]*)(\[.*\])[ \t]*$", re.M)
_FM_START = re.compile(r"^---\r?\n")
_FM_END = re.compile(r"\r?\n---\r?\n")


def _render_value(v):
    if isinstance(v, bool) or v is None:
        v = "" if v is None else str(v).lower()
    return v if isinstance(v, int) else json.dumps(v, ensure_ascii=False)


def _render_kv(k, v):
    if isinstance(v, list):                    # a block list, as Obsidian writes list properties
        return "%s:" % k + "".join("\n  - %s" % _render_value(x) for x in v)
    return "%s: %s" % (k, _render_value(v))


def render_record(rec):
    """Frontmatter: RECORD_KEYS in order (strings JSON-quoted, None as ""), the OPTIONAL_KEYS that are
    set, then the unknown keys (`extra`) verbatim; then the body as is."""
    out = ["---"] + ["%s: %s" % (k, _render_value(rec.get(k))) for k in RECORD_KEYS]
    out += [_render_kv(k, rec[k]) for k in OPTIONAL_KEYS if rec.get(k) is not None]
    extra = rec.get("extra") or ""
    return "\n".join(out) + "\n" + extra + ("" if not extra or extra.endswith("\n") else "\n") + \
        "---\n" + (rec.get("body") or "")


def _split_frontmatter(fm):
    """(known-key lines, unknown-key text): a top-level `key:` line and its indented lines go together."""
    known, extra, cur = [], [], None
    for line in fm.split("\n"):
        if line and not line[0].isspace() and not line.startswith("-"):
            key = line.split(":", 1)[0].strip() if ":" in line else None
            cur = known if key in RECORD_KEYS or key in OPTIONAL_KEYS else extra
        (cur if cur is not None else extra).append(line)
    return "\n".join(known), "".join(l + "\n" for l in extra)


def parse_record(text):
    """Inverse of render_record. Raises ValueError when the file is empty or half written, or when the
    frontmatter is missing or unreadable. CRLF inside the frontmatter is read; the body stays as is."""
    if not text.strip():
        raise ValueError("empty or still being written by a sync tool")
    start = _FM_START.match(text)
    if not start:
        raise ValueError("no frontmatter")
    end = _FM_END.search(text, start.end() - 1)
    if not end:
        raise ValueError("frontmatter not closed — empty or still being written by a sync tool")
    known, extra = _split_frontmatter(text[start.end():end.start()].replace("\r\n", "\n").replace("\r", "\n"))
    known = _FLOW_READ_BY.sub(lambda m: m.group(1) + json.dumps(m.group(2), ensure_ascii=False), known)
    meta = cc.read_yaml_subset(known)            # `read_by: [a, b]` typed by hand is read as text
    rec = {k: meta.get(k) for k in RECORD_KEYS}
    rec.update({k: (meta.get(k) if meta.get(k) != "" else None) for k in OPTIONAL_KEYS})
    rec["parent"] = rec["parent"] or None
    if not rec.get("id") or not isinstance(rec.get("order"), int):
        raise ValueError("frontmatter lacks id or order")
    rec["extra"] = extra.rstrip("\n") + "\n" if extra.strip() else ""
    rec["body"] = text[end.end():]
    return rec


def readers(rec):
    """The skills a custom or setting record is assigned to (`read_by`): a frozenset of lower-case names,
    where "all" means every skill; None when the key is unset or empty. Accepts "a, b", "[a, b]" and a list."""
    v = rec.get("read_by")
    if v is None:
        return None
    items = v if isinstance(v, list) else str(v).strip().strip("[]").split(",")
    names = frozenset(re.sub(r"\s+", "", str(x)).strip("\"'").lower() for x in items) - {""}
    return names or None


def unassigned_ids(records):
    """Ids of the custom records nobody reads in `ctx read` (no read_by), in record order."""
    return [r["id"] for r in sorted(records, key=lambda r: r["order"]) if r["type"] == "custom" and readers(r) is None]


STATUS_BEGIN = "<!-- ctx:begin id=status -->"
STATUS_END = "<!-- ctx:end id=status -->"
_STATUS_RE = re.compile(re.escape(STATUS_BEGIN) + r".*?" + re.escape(STATUS_END) + r"\r?\n?", re.S)


def has_status_region(body):
    return bool(_STATUS_RE.search(body or ""))


def clear_status_region(body):
    return _STATUS_RE.sub("", body or "", count=1)


def set_status_region(body, since, reason):
    """The `ctx` status region right after the record's first line (an existing one is replaced)."""
    body = clear_status_region(body)
    nl = "\r\n" if "\r\n" in body else "\n"
    block = STATUS_BEGIN + nl + "> ⚠ Неактуально з %s: %s" % (since, reason) + nl + STATUS_END + nl
    cut = body.find("\n")
    if cut < 0:
        return body + nl + block
    return body[:cut + 1] + block + body[cut + 1:]


def compile_records(records):
    """The compiled local-context.md: record bodies in ascending `order`."""
    return "".join(r["body"] for r in sorted(records, key=lambda r: r["order"]))


# ------------------------------------------------------------------ store I/O
class StoreError(Exception):
    """A record or the store cannot be read (exit 3)."""


class RegionError(Exception):
    """An edit would land inside a provider's managed region (exit 4)."""


class PathRefused(Exception):
    """A write would land outside ~/.grow-pm and the storage root (exit 4)."""


WRITE_ROOTS = None


@contextlib.contextmanager
def guard_roots(roots):
    """Every write and delete inside the block must land, after realpath, under one of `roots`."""
    global WRITE_ROOTS
    prev = WRITE_ROOTS
    WRITE_ROOTS = tuple(os.path.realpath(r) for r in roots if r)
    try:
        yield WRITE_ROOTS
    finally:
        WRITE_ROOTS = prev


def check_target(path):
    """The target's realpath; outside the guarded roots → PathRefused (no check without a guard)."""
    rp = os.path.realpath(path)
    if WRITE_ROOTS is not None and not any(rp == r or rp.startswith(r.rstrip(os.sep) + os.sep) for r in WRITE_ROOTS):
        raise PathRefused("%s is outside ~/.grow-pm and the storage root" % path)
    return rp


READ_TIMEOUT_S = 30.0
_BUDGET = threading.local()     # `until`: the time.monotonic() moment the innermost read_budget of this thread ends


def read_timeout():
    """Seconds a ctx run waits for its files in all; GROW_PM_CTX_READ_TIMEOUT overrides. Inside `read_budget` (since
    v3.14), no more than what is left of it — 0 once it is spent."""
    try:
        own = float(os.environ.get("GROW_PM_CTX_READ_TIMEOUT") or READ_TIMEOUT_S)
    except ValueError:
        own = READ_TIMEOUT_S
    until = getattr(_BUDGET, "until", None)
    return own if until is None else min(own, max(0.0, until - time.monotonic()))


def budget_until():
    """The time.monotonic() moment the innermost `read_budget` of this thread ends, or None outside one (since v3.14.0:
    the card reads its registrations by it inside the daily sync, `ctx_ops.card_repos`)."""
    return getattr(_BUDGET, "until", None)


@contextlib.contextmanager
def read_budget(seconds):
    """A time budget for every read in the block that asks `read_timeout()` (read_text, Store._texts …): `seconds`
    from now, None for none. A block inside another ends no later than the outer one — the smaller wins. The budget
    is the calling thread's: an unattended sync that keeps one never cuts the reads of another thread."""
    prev = getattr(_BUDGET, "until", None)
    if seconds is not None:
        until = time.monotonic() + seconds
        _BUDGET.until = until if prev is None else min(prev, until)
    try:
        yield
    finally:
        _BUDGET.until = prev


def read_text(path, timeout=None):
    """The file's text byte for byte, read in a helper thread: an iCloud-evicted file blocks in open()
    until it downloads. Not there within `timeout` seconds → StoreError naming it; OSError and
    UnicodeDecodeError come back as they are."""
    return _read_in_thread(path, timeout, binary=False)


def read_bytes(path, timeout=None):
    """`read_text` for a file that need not be text (since v3.14.0: a snapshot copies the store's files as they are —
    an attachment Obsidian put next to a record too): its bytes, in the same helper thread and time budget."""
    return _read_in_thread(path, timeout, binary=True)


def _read_in_thread(path, timeout, binary):
    timeout = read_timeout() if timeout is None else timeout
    box = {}

    def work():
        try:
            with (open(path, "rb") if binary else open(path, encoding="utf-8", newline="")) as f:
                box["text"] = f.read()
        except BaseException as e:  # handed back to the caller below
            box["error"] = e

    t = threading.Thread(target=work, daemon=True)
    t.start()
    t.join(max(timeout, 0.05))
    if t.is_alive():
        raise StoreError("not available locally: %s did not load within %g s — still downloading (iCloud) or "
                         "syncing; open the vault so it downloads, then run again; nothing was written"
                         % (os.path.basename(path), timeout))
    if "error" in box:
        raise box["error"]
    return box["text"]


def atomic_write(path, text):
    """Write `text` byte for byte through a hidden temp file in the same folder, then replace."""
    check_target(path)
    folder = os.path.dirname(path) or "."
    os.makedirs(folder, exist_ok=True)
    tmp = os.path.join(folder, ".%s.tmp" % os.path.basename(path))
    try:
        with open(tmp, "w", encoding="utf-8", newline="") as f:
            f.write(text)
        os.replace(tmp, path)
    except BaseException:
        if os.path.exists(tmp):
            os.remove(tmp)
        raise


TMP_STALE_S = 24 * 3600                 # an atomic_write temp file older than this was left by a write that never finished
TMP_NAME = re.compile(r"^\..+\.tmp$")   # …and its name: `.<name>.tmp`, in the folder of the file it was for


def remove_stale_tmp(folder, older_than=TMP_STALE_S):
    """Remove the temp files `atomic_write` names (`.<name>.tmp`) directly in `folder` that were last changed more than
    `older_than` seconds ago — what a write cut short (a crash, a kill, a full disk) left behind; no write is still at it a
    day later (since v3.14.0). Only regular files: a folder or a link of that name is left, so is a subfolder's file. Each
    goes through check_target; one that is refused or cannot be removed stays. A folder that is a link or is not there
    is nothing to do. Never raises; returns the names removed."""
    removed = []
    if os.path.islink(folder):
        return removed
    try:
        names = sorted(os.listdir(folder))
    except OSError:
        return removed
    now = time.time()
    for name in names:
        if not TMP_NAME.match(name):
            continue
        path = os.path.join(folder, name)
        try:
            st = os.lstat(path)
            if not stat.S_ISREG(st.st_mode) or now - st.st_mtime <= older_than:
                continue
            check_target(path)
            os.remove(path)
        except (OSError, PathRefused):
            continue
        removed.append(name)
    return removed


ID_RE = re.compile(r"^[a-z0-9][a-z0-9.-]*$")


class Store:
    """`{root}/records/<id>.md`, `{root}/INDEX.md`, `{root}/.state/{compiled.json, journal.jsonl}` and, since v3.13.0,
    `{root}/.state/blocks/` — a repository's block state `<repo>.json` and its base texts `<repo>/<sha>.md`
    (ctx_blocks.py keeps them; a snapshot copies them with the rest of `.state/`). Since v3.14.0 `{root}/sync/` holds
    the daily sync's reports, `YYYY-MM-DD.md` (ctx_synced.py writes them for the user to read in the vault): not records,
    so `stray_files` and `validate` never look there, and not part of a snapshot, so `ctx undo` leaves them."""

    def __init__(self, root):
        self.root = root
        self.sync_dir = os.path.join(root, "sync")
        self.records_dir = os.path.join(root, "records")
        self.state_dir = os.path.join(root, ".state")
        self.card_path = os.path.join(root, "INDEX.md")
        self.archive_dir = os.path.join(root, "archive")
        self.overlays_dir = os.path.join(root, "overlays")          # since v3.23.0: overlays/<repo>.yaml (ctx_overlay.py)

    def exists(self):
        return os.path.isdir(self.state_dir)

    def record_files(self):
        if not os.path.isdir(self.records_dir):
            return [], []
        valid, stray = [], []
        for name in sorted(os.listdir(self.records_dir)):
            if name.startswith(".") or not name.endswith(".md"):
                continue
            (valid if ID_RE.match(name[:-3]) else stray).append(name)
        return valid, stray

    def _texts(self, names):
        """{name: text} of record files, all read within one time budget (read_timeout)."""
        out, deadline = {}, time.time() + read_timeout()
        for name in names:
            try:
                out[name] = read_text(os.path.join(self.records_dir, name), max(deadline - time.time(), 0.05))
            except (OSError, UnicodeDecodeError) as e:
                raise StoreError("record not readable: %s (%s)" % (name, e))
        return out

    def load(self):
        """Records sorted by `order`. A record that cannot be read in time or parsed → StoreError naming its file."""
        out = []
        valid, _ = self.record_files()
        texts = self._texts(valid)
        for name in valid:
            text = texts[name]
            try:
                rec = parse_record(text)
            except ValueError as e:
                raise StoreError("record not valid: %s (%s)" % (name, e))
            if rec["id"] != name[:-3]:
                continue                       # a copy under another name (a sync conflict) — stray
            out.append(rec)
        return sorted(out, key=lambda r: r["order"])

    def stray_files(self):
        """Files in records/ that compile ignores: other names, or a record's copy under another name."""
        valid, stray = self.record_files()
        for name in valid:
            try:
                if parse_record(read_text(os.path.join(self.records_dir, name)))["id"] != name[:-3]:
                    stray.append(name)
            except (OSError, UnicodeDecodeError, ValueError, StoreError):
                pass
        return sorted(stray)

    def archived(self):
        """Archived records (`archive/<year>/<id>.md`), each with its `path`."""
        out = []
        if os.path.isdir(self.archive_dir):
            for year in sorted(os.listdir(self.archive_dir)):
                folder = os.path.join(self.archive_dir, year)
                for name in sorted(os.listdir(folder)) if os.path.isdir(folder) else []:
                    if name.endswith(".md") and ID_RE.match(name[:-3]):
                        try:
                            out.append(dict(parse_record(read_text(os.path.join(folder, name))),
                                            path=os.path.join(folder, name)))
                        except (OSError, UnicodeDecodeError, ValueError, StoreError):
                            continue
        return out

    def reserved_ids(self):
        """Ids a new record may not take: the archived ones."""
        return {r["id"] for r in self.archived()}

    def write(self, rec):
        """A live record: `status` follows the ctx status region (invalid) — absent means active."""
        rec = dict(rec, sha=sha_text(rec.get("body") or ""), status="invalid" if has_status_region(rec.get("body")) else None)
        atomic_write(os.path.join(self.records_dir, rec["id"] + ".md"), render_record(rec))
        return rec

    def remove(self, rec_id):
        path = os.path.join(self.records_dir, rec_id + ".md")
        if os.path.exists(path):
            check_target(path)
            os.remove(path)

    def state(self):
        path = os.path.join(self.state_dir, "compiled.json")
        if not os.path.isfile(path):
            return {}
        with open(path, encoding="utf-8") as f:
            return json.load(f)

    def save_state(self, state):
        atomic_write(os.path.join(self.state_dir, "compiled.json"),
                     json.dumps(state, ensure_ascii=False, indent=1, sort_keys=True) + "\n")

    def journal(self, entry):
        os.makedirs(self.state_dir, exist_ok=True)
        with open(check_target(os.path.join(self.state_dir, "journal.jsonl")), "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False, sort_keys=True) + "\n")

    def journal_entries(self):
        path = os.path.join(self.state_dir, "journal.jsonl")
        if not os.path.isfile(path):
            return []
        with open(path, encoding="utf-8") as f:
            return [json.loads(l) for l in f if l.strip()]


# --------------------------------------------------------------- field edits
FIELD_RE = re.compile(r"^- \*\*(?P<name>[^*\n]+?):\*\*[ \t]*(?P<value>[^\r\n]*)")


def _lines(body):
    """[(offset, line_without_ending, ending)] for every line of the body."""
    out, pos = [], 0
    for ln in body.splitlines(keepends=True):
        core = ln.rstrip("\r\n")
        out.append((pos, core, ln[len(core):]))
        pos += len(ln)
    return out


def _in_region(off, spans):
    return any(a <= off < b for a, b in spans)


def field_get(body, name):
    """Value of the first `- **<name>:** value` line outside managed regions, or None."""
    spans = cc.managed_spans(body)
    for off, core, _ in _lines(body):
        m = FIELD_RE.match(core)
        if m and m.group("name").strip() == name and not _in_region(off, spans):
            return m.group("value").strip()
    return None


def field_set(body, name, value):
    """Replace the field's line; an absent field goes after the last line of the first bullet list.
    A field present only inside a managed region → RegionError."""
    spans, lines = cc.managed_spans(body), _lines(body)
    new = "- **%s:** %s" % (name, value)
    inside = False
    for off, core, end in lines:
        m = FIELD_RE.match(core)
        if m and m.group("name").strip() == name:
            if _in_region(off, spans):
                inside = True
                continue
            return body[:off] + new + body[off + len(core):]
    if inside:
        raise RegionError("field %r is inside a provider's managed region" % name)
    first = next((k for k, (off, core, _) in enumerate(lines)
                  if core.startswith("- ") and not _in_region(off, spans)), None)
    if first is None:
        off, core, end = lines[0]
        at, end = off + len(core) + len(end), end or "\n"
    else:
        last = first
        while last + 1 < len(lines) and lines[last + 1][1].startswith("- "):
            last += 1
        off, core, end = lines[last]
        at, end = off + len(core) + len(end), end or "\n"
        if not lines[last][2]:
            return body + "\n" + new
    return body[:at] + new + end + body[at:]


def _level(core):
    m = re.match(r"^(#{1,6}) ", core)
    return len(m.group(1)) if m else 0


def append_line(body, text, under=None):
    """Add `text` after the last non-empty line of the body, or of the subsection whose heading line is
    `under` (up to the next heading of the same or a higher level); a table row (since v3.22.0) after the last row of
    the first table there. An identical line there → unchanged;
    a place inside a provider's managed region → RegionError."""
    lines, spans = _lines(body), cc.managed_spans(body)
    lo, hi = 0, len(lines)
    if under is not None:
        lo = next((k for k, (_, core, _) in enumerate(lines) if core.strip() == under.strip()), None)
        if lo is None:
            raise ValueError("subsection not found: %s" % under)
        lvl = _level(lines[lo][1])
        hi = next((k for k in range(lo + 1, len(lines)) if 0 < _level(lines[k][1]) <= lvl), len(lines))
    if any(core.rstrip() == text.rstrip() for _, core, _ in lines[lo:hi]):
        return body
    last = max((k for k in range(lo, hi) if lines[k][1].strip()), default=lo)
    if text.lstrip().startswith("|"):                   # since v3.22.0: a table row goes after the table's last row,
        rows = [k for k in range(lo, hi) if lines[k][1].strip().startswith("|")]    # not after a note below it
        if rows:
            last = rows[0]
            while last + 1 < hi and lines[last + 1][1].strip().startswith("|"):
                last += 1
    off, core, end = lines[last]
    at = off + len(core) + len(end)
    if _in_region(at if end else off + len(core), spans):
        raise RegionError("the line would land inside a provider's managed region%s"
                          % (" (under %s)" % under.strip() if under else ""))
    if not end:
        return body[:off + len(core)] + "\n" + text + body[off + len(core):]
    return body[:at] + text + end + body[at:]


# ------------------------------------------------------------- context card
CARD_MAX = 200
_EMPTY = ("", "_none_", "none", "—", "-", "n/a")


def _heading_text(core):
    m = re.match(r"^#{1,6} (.*)$", core.lstrip("﻿"))
    return m.group(1).strip() if m else None


def _member_count(body):
    """Rows of the first table after a `Members` heading in your own text; failing that, in a managed region (the
    team block of a repository). None when there is none (names never leave)."""
    count = _table_rows_after_members(cc.strip_managed_regions(body))
    if count is None:
        for start, end in cc.managed_spans(body):
            count = _table_rows_after_members(body[start:end])
            if count is not None:
                break
    return count


SECTION_ALIASES = {"members": ("Team Members",)}   # since v3.14.1: other headings a subsection is also found under


def section_names(name):
    """`name` and the other headings it is also found under (SECTION_ALIASES), in the order they are tried."""
    return (name,) + SECTION_ALIASES.get(name.lower(), ())


def _members_heading(core):
    return (_heading_text(core) or "").startswith("Members") or any(heading_matches(core, a) for a in SECTION_ALIASES["members"])


def _table_rows_after_members(body):
    lines = [core for _, core, _ in _lines(body)]
    at = next((k for k, c in enumerate(lines) if _members_heading(c)), None)
    if at is None:
        return None
    rows = []
    for c in lines[at + 1:]:
        if _heading_text(c) is not None:
            break
        if c.strip().startswith("|"):
            rows.append(c)
        elif rows and c.strip():
            break
    return max(len(rows) - 2, 0) if rows else None


def heading_matches(core, name):
    """A heading whose text is `name` or starts with it followed by a non-word character
    ("Key Metrics (focus)" answers "Key Metrics"; "Localesx" does not answer "Locales")."""
    text = (_heading_text(core) or "").lower()
    want = name.lower()
    return _level(core) > 0 and (text == want or (text.startswith(want) and not text[len(want)].isalnum()))


def _bullets_under(body, name):
    lines = [core for _, core, _ in _lines(body)]
    at = next((k for k, c in enumerate(lines) if heading_matches(c, name)), None)
    out = []
    for c in lines[at + 1:] if at is not None else []:
        if _heading_text(c) is not None:
            break
        if c.startswith("- "):
            out.append(c[2:].strip())
    return out


def _cell(s):
    s = s.replace("|", "\\|")
    return s if len(s) <= 80 else s[:79] + "…"


def _summary(rec):
    if rec["type"] == "team":
        n = _member_count(rec["body"])
        return "%d members" % n if n is not None else "—"
    if rec["type"] == "setting" and rec["title"].startswith("People"):
        return "(people settings — open the record)"
    fence = False
    for _, core, _ in _lines(rec["body"]):
        s = core.strip().lstrip("﻿")
        if s.startswith("```"):
            fence = not fence
            continue
        if fence or not s or _heading_text(s) is not None or s.startswith(("|", "<!--")):
            continue
        for mark in ("- ", "> "):
            if s.startswith(mark):
                s = s[len(mark):].strip()
                break
        return _cell(s)
    return "—"


def blocks_word(n):
    """The form of "блок" after the number `n`: блок for 1, 21, 101 …; блоки for 2–4, 22–24 …; блоків for the rest and 11–14."""
    if n % 10 == 1 and n % 100 != 11:
        return "блок"
    return "блоки" if n % 10 in (2, 3, 4) and n % 100 not in (12, 13, 14) else "блоків"


def build_card(records, compiled_text, now, stale=(), archived=0, repos=(), repos_line=None):
    """INDEX.md: who, onboarding, products, teams, vaults and providers, then one row per record; ≤ CARD_MAX lines.
    `stale` maps a stale record's id to its verified date (its row ends with ⚠ <date>); `archived` counts the
    archived records; `repos` is [{"id", "blocks", "v", "checked"}] — the repositories that put blocks in the
    records, as ctx_ops.card_repos gives them — and makes one line, `- **Repos:** <id>: <N> блок(и|ів) · v<v> · перевірено
    <date>; …` (a version or a date nobody knows is left out). `repos_line`, when given, is that line as it is — the
    one the card had, kept while a registration cannot be read (ctx_ops.store_card, since v3.13.1)."""
    import ctx_schema as sc                    # here: ctx_schema imports this module
    fields = sc.load_fields().get("product", {})
    stale = stale if isinstance(stale, dict) else {i: "" for i in stale}
    recs = sorted(records, key=lambda r: r["order"])
    first = lambda t: next((r for r in recs if r["type"] == t), None)
    over = []
    prof = first("profile")
    if prof:
        name, role, lang = (field_get(prof["body"], k) for k in ("Name", "Role", "Language"))
        parts = [name] if name else []
        parts += ["role %s" % role] if role else []
        parts += ["language %s" % lang] if lang else []
        over.append("- **Who:** " + " · ".join(parts))
    onb = first("onboarding")
    if onb:
        mode, deferred = field_get(onb["body"], "Mode"), field_get(onb["body"], "Deferred steps")
        over.append("- **Onboarding:** %s · deferred: %s" % (mode or "—", "—" if (deferred or "").strip() in _EMPTY else deferred))
    for r in recs:
        if r["type"] == "product":
            parts = []
            jira = sc.raw_value(r["body"], "Jira Project Key", fields.get("Jira Project Key", {}))
            space = sc.raw_value(r["body"], "Confluence Space", fields.get("Confluence Space", {}))
            parts += ["Jira %s" % jira] if jira else []
            parts += ["Confluence %s" % space] if space else []
            spec = fields.get("Platforms", {"type": "list"})
            plats = sc.parse_value(spec, sc.raw_value(r["body"], "Platforms", spec)) or []
            parts += ["platforms %s" % ", ".join(plats)] if plats else []
            over.append("- **Product:** %s%s" % (r["title"].split(":", 1)[-1].strip(), " — " + " · ".join(parts) if parts else ""))
    for r in recs:
        if r["type"] == "team":
            n = _member_count(r["body"])
            over.append("- **Team:** %s%s" % (r["title"].split(":", 1)[-1].strip(), " — %d members" % n if n is not None else ""))
    vaults = ", ".join("%s (%s)" % (f or os.path.basename(p), m or "auto") for p, f, m in cc.vault_modes(compiled_text)) or "—"
    provs = ", ".join(b["id"] for b in cc.vault_search_bullets(compiled_text)) or "—"
    over.append("- **Vaults:** %s · **Providers:** %s" % (vaults, provs))
    if repos_line:
        over.append(repos_line)
    elif repos:
        over.append("- **Repos:** " + "; ".join(
            " · ".join(["%s: %d %s" % (r["id"], r["blocks"], blocks_word(r["blocks"]))] + (["v%s" % r["v"]] if r.get("v") else [])
                       + (["перевірено %s" % r["checked"][:10]] if r.get("checked") else [])) for r in repos))
    if stale:
        over.append("- **Застарілі:** %d — ctx verify --stale або конфігуратор" % len(stale))
    if archived:
        over.append("- **Архів:** %d — ctx list --archived" % archived)
    head = ["# Context card",
            "> Generated by ctx from %d records on %s. Edit local-context.md or the records, not this card." % (len(recs), now),
            ""]
    table = ["| Record | Title | Summary | Modified |", "|---|---|---|---|"]
    rows = ["| %s | %s | %s | %s%s |" % (r["id"], _cell(r["title"]), _summary(r), (r.get("modified") or "")[:10],
                                          " ⚠ %s" % stale[r["id"]] if r["id"] in stale else "") for r in recs]
    fixed = len(head) + len(over) + 1 + len(table)
    if fixed + len(rows) > CARD_MAX:
        keep = max(CARD_MAX - fixed - 1, 0)
        rows = rows[:keep] + ["| … | +%d more — ctx list | | |" % (len(rows) - keep)]
    return "\n".join(head + over + [""] + table + rows) + "\n"
