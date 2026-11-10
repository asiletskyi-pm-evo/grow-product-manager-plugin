#!/usr/bin/env python3
"""publications.py — the record of where a result was published (references/artifact-publishing.md §5–§7).

  find    the publication record of a result: its key file (`--key`, ~/.grow-pm/publications/<key>.yaml), else
          the note's `published` field (`--note`); the older confluence_page_id / confluence_url / published_to
          (a Confluence page) and a v4.2.0 board.yaml's artifact_id read as a record of version 1
  record  one version of one place: the first one, the next one of the same id, or a place created anew on the
          same host and level (the old id goes to `replaced`); written to the key file, and mirrored into the note
  share   the audience of a recorded place after it was shared — never its version or time
  forget  one place out of a result's record, on the user's word (the place itself is not touched)
  digest  the byte length and the base64 SHA-256 of a file — what an upload to a pre-signed link needs

The record of one result lives in ONE file, whichever run saved which note: the key file, a YAML state file whose
top-level `published` is a list of flat entries (surface, kind, level, id, url, version, published, audience,
replaced, remote_version). The note the run saved gets the same list in its frontmatter field `published` — a
mirror; only that field is written, and every other byte of the note stays as it was. A link or an id with a user or a password, a token, a signature or a
pre-signed query — in the query, the fragment or a path parameter, encoded or not — is refused, by kind, never
echoed (ctx_never and the rules below). Every command ends with one `PUB_RESULT {json}` line. Stdlib only
(Python 3.9). Exit 0; 2 for wrong arguments, a refused value, a file that is not there or a `published` field
that does not read (it is never overwritten); 1 when the file cannot be written.
"""
import argparse, base64, datetime, hashlib, json, os, re, sys, tempfile
from urllib.parse import urlsplit, unquote

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import ctx_common as cc  # noqa: E402
import ctx_never as cn  # noqa: E402

KINDS = ("deck", "dashboard", "document", "page", "board", "design")
SURFACES = ("artifact", "docs", "confluence")          # plus the id of a tools-registry record
AUDIENCES = ("private", "shared", "space:<KEY>", "unknown")
FIELDS = ("surface", "kind", "level", "id", "url", "version", "published", "audience", "replaced", "remote_version",
          "key")
LEVELS = ("typed", "page")                              # an ARTIFACT's level: two places on one host
KEY = re.compile(r"^[^\W_][\w.-]{0,79}(?:/[^\W_][\w.-]{0,79}){0,3}\Z")   # lower-case words, Cyrillic too
BOARD_KEYS = ("artifact_id", "artifact_url", "board_id", "board_url", "live_board_id", "live_board_url")
SLUG = re.compile(r"^[a-z0-9][a-z0-9-]{0,63}$")
SPACE = re.compile(r"^space:[A-Z0-9][A-Z0-9_]{0,31}$")  # a team space's key; a personal space is `private`
AT = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(?::\d{2})?(?:Z|[+-]\d{2}:\d{2})?$")
# A parameter that carries a credential: a token, a key, a signature, a session, a pre-signed link's parts.
CRED = (r"x-amz-[\w-]*|x-goog-[\w-]*|[\w-]*token[\w-]*|[\w-]*secret[\w-]*|[\w-]*passw[\w-]*|[\w-]*signature[\w-]*|"
        r"[\w-]*access[_-]?key[\w-]*|[\w-]*hmac[\w-]*|sig|skoid|sktid|key|key-pair-id|apikey|api_key|api-key|auth|"
        r"authorization|bearer|code|credential|policy|expires|jwt|otp|pwd|pass|ticket|session|sessionid|jsessionid|"
        r"phpsessid|sid|[\w-]*auth[_-]?key|[\w-]*private[_-]?key|rlkey|asp\.net_sessionid|hdnts")
CRED_PARAM = re.compile(r"(?:^|[?&;#/~])\s*(?:%s)\s*(?:\[\])?\s*=" % CRED, re.I)
EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.\w")
MAX_ID, MAX_URL, MAX_RV = 300, 2000, 64
KEY_LINE = re.compile(r"^published[ \t]*:(?P<val>.*)$")
TOP = re.compile(r"^[^\s#-]")                           # a line that opens another top-level key


def result(**kw):
    print("PUB_RESULT " + json.dumps(kw, ensure_ascii=False, sort_keys=True))


def _decoded(s):
    """`s` with percent-encoding undone until it stops changing (at most three passes)."""
    for _ in range(3):
        t = unquote(s)
        if t == s:
            break
        s = t
    return s


def cred_problem(text):
    """A credential's kind in a link or an id — the never-store filter, then a credential-named parameter in the
    query, the fragment or a path parameter, encoded or not; None when clean. Never the value."""
    d = _decoded(text)
    kinds = cn.scan(text) or cn.scan(d)
    if kinds:
        return "a secret (%s)" % ",".join(kinds)
    if CRED_PARAM.search(d):
        return "a credential in a parameter"
    try:
        rest = urlsplit(d)
        after = d if not rest.netloc else d.split(rest.netloc, 1)[1]
    except ValueError:
        after = d
    if EMAIL.search(after):
        return "an e-mail in the link"
    return None


def link_problem(url):
    """Why `url` may not be recorded, or None — a kind, never the value."""
    if not isinstance(url, str) or not url or len(url) > MAX_URL or re.search(r"\s", url):
        return "not a link"
    try:
        parts = urlsplit(url)
    except ValueError:
        return "not a link"
    if parts.scheme not in ("https", "http") or not parts.hostname:
        return "not a web link"
    if "@" in parts.netloc or "@" in _decoded(parts.netloc):
        return "a user or a password in the link"
    bad = cred_problem(url)
    return ("%s in the link" % bad) if bad else None


def value_problem(name, v, limit=MAX_ID):
    if not isinstance(v, str) or not v or len(v) > limit or re.search(r"[\x00-\x1f\x7f\s]", v):
        return "%s is empty, too long or has spaces or control characters" % name
    if "://" in v:                                     # an id that is a link (an ARTIFACT's) is checked as a link
        bad = link_problem(v)
        return ("%s: %s" % (name, bad)) if bad else None
    bad = cred_problem(v)
    return ("%s in %s" % (bad, name)) if bad else None


# ------------------------------------------------------------------ the file
def _frontmatter(text):
    """(start, end, eol) of the first frontmatter by the index's rules (ctx_index): BOMs before it, an opening line
    `---`, closed by the first line `---` or `...`; `start` after the opening line, `end` where the closing line
    begins. None when the note has none."""
    i = len(text) - len(text.lstrip("﻿"))
    nl = text.find("\n", i)
    if nl < 0 or text[i:nl].rstrip("\r ") != "---":
        return None
    start = pos = nl + 1
    eol = "\r\n" if text[i:nl].endswith("\r") else "\n"
    while pos <= len(text):
        nl = text.find("\n", pos)
        line = text[pos:] if nl < 0 else text[pos:nl]
        if line.rstrip("\r ") in ("---", "..."):
            return start, pos, eol
        if nl < 0:
            return None
        pos = nl + 1
    return None


class Unreadable(Exception):
    pass


class Foreign(Exception):
    """The note's own `published` property is something else (a date, a flag, a list of words)."""


def _doc(text, is_yaml):
    """(start, end, eol) of the YAML text that holds `published` — the frontmatter, or the whole YAML file."""
    if is_yaml:
        return 0, len(text), "\r\n" if "\r\n" in text else "\n"
    return _frontmatter(text)


def _key_line(name):
    return KEY_LINE if name == "published" else re.compile(r"^%s[ \t]*:(?P<val>.*)$" % re.escape(name))


def _block(text, start, end, name="published"):
    """(b0, b1) — the top-level key `name` and its own lines (indented or `-` items) inside text[start:end], or None.
    Blank lines and column-0 comments after its last own line are the note's, not the field's."""
    key_line = _key_line(name)
    pos, b0, b1 = start, None, None
    while pos < end:
        nl = text.find("\n", pos, end)
        stop = end if nl < 0 else nl + 1
        line = text[pos:stop].rstrip("\r\n")
        if b0 is None:
            if key_line.match(line):
                b0, b1 = pos, stop
        elif not line.strip() or line.startswith("#"):
            pass
        elif TOP.match(line):
            break
        else:
            b1 = stop
        pos = stop
    return (b0, b1) if b0 is not None else None


def _scalar_fields(text, start, end):
    """The top-level `key: value` scalars of text[start:end] that the older records used."""
    out = {}
    names = "published_to|confluence_page_id|confluence_url|" + "|".join(BOARD_KEYS)
    for line in text[start:end].splitlines():
        m = re.match(r"^(%s)[ \t]*:[ \t]*(.*?)[ \t]*$" % names, line)
        if m and m.group(2):
            try:
                v = cc._scalar(cc._strip_comment(m.group(2)), 0)
            except ValueError:
                continue
            if isinstance(v, (str, int)) and str(v).strip():
                out[m.group(1)] = str(v).strip()
    return out


def _entry(e):
    """An entry as read from the note, with its types made sound — raises Unreadable."""
    if not isinstance(e, dict) or not e.get("surface") or not e.get("kind"):
        raise Unreadable("an entry without surface or kind")
    out = dict(e)
    for k in ("surface", "kind", "level", "id", "url", "published", "audience", "remote_version", "key"):
        if out.get(k) is not None and not isinstance(out[k], list):
            out[k] = str(out[k])
    try:
        v = float(str(e.get("version") or 1))
        if v != v or v in (float("inf"), float("-inf")) or v < 1:
            raise ValueError
        out["version"] = int(v)
    except (ValueError, OverflowError):
        raise Unreadable("a version that is not a whole number from 1")
    for k in [k for k in out if k not in FIELDS]:          # a field someone added stays only when it is harmless
        v = out[k]
        if isinstance(v, list) or not isinstance(v, (str, int)) or len(str(v)) > 100 or cred_problem(str(v)):
            out.pop(k)
    rep = e.get("replaced")
    rep = [rep] if isinstance(rep, (str, int)) and str(rep).strip() else rep if isinstance(rep, list) else []
    out["replaced"] = [str(x) for x in rep if str(x).strip() and str(x) != "None"]
    if not out["replaced"]:
        out.pop("replaced")
    return out


def load(path):
    """(text, is_yaml, entries, legacy) — raises OSError, Unreadable or Foreign."""
    with open(path, encoding="utf-8", newline="") as f:
        text = f.read()
    is_yaml = path.lower().endswith((".yaml", ".yml"))
    doc = _doc(text, is_yaml)
    if not doc:
        return text, is_yaml, [], {}
    start, end, _ = doc
    span = _block(text, start, end)
    legacy = _scalar_fields(text, start, end)
    if not span:
        return text, is_yaml, [], legacy
    first = text[span[0]:span[1]].split("\n", 1)[0].rstrip("\r")
    val = cc._strip_comment(KEY_LINE.match(first).group("val")).strip()
    if val not in ("", "[]"):
        raise Foreign()
    try:
        raw = cc.read_yaml_records(text[span[0]:span[1]], "published")
    except ValueError as e:
        if "list of mappings" in str(e):              # a list of words or a mapping: the note's own property
            raise Foreign()
        raise Unreadable(str(e))
    return text, is_yaml, [_entry(e) for e in raw], legacy


def legacy_entry(legacy):
    """The older fields as a `confluence` record — only when they name a Confluence page by its id."""
    url = legacy.get("confluence_url") or legacy.get("published_to") or ""
    pid = legacy.get("confluence_page_id") or ""
    if not pid and "/wiki/" in url:
        m = re.search(r"/pages/(\d+)", url)
        pid = m.group(1) if m else ""
    if not pid or (url and link_problem(url)):
        return None
    return {"surface": "confluence", "kind": "page", "id": pid, "url": url, "version": 1, "legacy": True}


def board_entry(legacy):
    """A v4.1.0–v4.2.0 board.yaml's live board (its id or link under one of BOARD_KEYS) as an `artifact` record."""
    bid = next((legacy[k] for k in ("artifact_id", "board_id", "live_board_id") if legacy.get(k)), "")
    url = next((legacy[k] for k in ("artifact_url", "board_url", "live_board_url") if legacy.get(k)), "") or \
        (bid if "://" in bid else "")
    if not (bid or url) or value_problem("the id", bid or url) or (url and link_problem(url)):
        return None
    return {"surface": "artifact", "kind": "dashboard", "level": "typed", "id": bid or url, "url": url, "version": 1,
            "legacy": True}


def _legacy(legacy, is_yaml):
    lg = [legacy_entry(legacy)] + ([board_entry(legacy)] if is_yaml else [])
    return [e for e in lg if e]


def _clean(entries):
    """(entries, dropped) — an entry whose link or id would not pass `record` is never copied on."""
    keep = [e for e in entries if not value_problem("the id", e.get("id") or "x") and
            not (e.get("url") and link_problem(e["url"]))]
    return keep, len(entries) - len(keep)


def _q(v):
    return json.dumps(str(v), ensure_ascii=False)


def render(entries, eol):
    lines = ["published:"]
    for e in entries:
        lines.append("  - surface: %s" % e["surface"])
        lines.append("    kind: %s" % e["kind"])
        if e.get("level"):
            lines.append("    level: %s" % e["level"])
        for k in ("id", "url"):
            lines.append("    %s: %s" % (k, _q(e.get(k, ""))))
        lines.append("    version: %d" % int(e.get("version") or 1))
        if e.get("published"):
            lines.append("    published: %s" % _q(e["published"]))
        lines.append("    audience: %s" % _q(e.get("audience") or "unknown"))
        if e.get("remote_version"):
            lines.append("    remote_version: %s" % _q(e["remote_version"]))
        if e.get("key"):
            lines.append("    key: %s" % _q(e["key"]))
        if e.get("replaced"):
            lines.append("    replaced: [%s]" % ", ".join(_q(x) for x in e["replaced"]))
        for k in sorted(k for k in e if k not in FIELDS and k != "legacy"):   # a field someone added stays
            v = e[k]
            lines.append("    %s: %s" % (k, "[%s]" % ", ".join(_q(x) for x in v) if isinstance(v, list) else _q(v)))
    return eol.join(lines) + eol


def write(path, text, is_yaml, entries):
    write_field(path, text, is_yaml, "published", lambda eol: render(entries, eol))


def write_field(path, text, is_yaml, name, block_for):
    """Put the top-level field `name` — `block_for(eol)` gives its lines, the key line first — into the frontmatter of
    `text` (or the whole YAML file), replacing the field's own lines or adding it before the closing line; every other
    byte stays as it was, and the file is replaced atomically where it lives (a link kept). Shared with story_map.py
    (`baseline`), so both fields are written by one code path."""
    doc = _doc(text, is_yaml)
    if doc is None:                                  # a note without a frontmatter: one in front, the rest as it was
        eol = "\r\n" if "\r\n" in text else "\n"
        bom = "﻿" if text.startswith("﻿") else ""
        new = bom + "---" + eol + block_for(eol) + "---" + eol + text[len(bom):]
    else:
        start, end, eol = doc
        span = _block(text, start, end, name)
        block = block_for(eol)
        if span:
            new = text[:span[0]] + block + text[span[1]:]
        else:
            pre = text[:end]
            if pre and not pre.endswith("\n"):         # a YAML file without its last line ending
                pre += eol
            new = pre + block + text[end:]
    real = os.path.realpath(path)                    # a linked note is written where it lives, the link kept
    mode = os.stat(real).st_mode & 0o7777
    fd, tmp = tempfile.mkstemp(prefix=".pub-", dir=os.path.dirname(real))
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as f:
            f.write(new)
        os.chmod(tmp, mode)
        os.replace(tmp, real)
    except BaseException:
        if os.path.exists(tmp):
            os.remove(tmp)
        raise


# ------------------------------------------------------------------ commands
def _now():
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _host(url):
    try:
        return (urlsplit(url or "").hostname or "").lower()
    except ValueError:
        return ""


def _open(path, what="the note"):
    """(text, is_yaml, entries, legacy), "foreign", or an exit code after the result line."""
    if not path or not os.path.isfile(path):
        result(error="%s is not there" % what)
        return 2
    try:
        return load(path)
    except Foreign:
        return "foreign"
    except Unreadable as e:
        result(error="the published field of %s does not read — fix it there: %s" % (what, e))
        return 2
    except (OSError, UnicodeDecodeError) as e:
        result(error="%s does not read: %s" % (what, getattr(e, "strerror", None) or type(e).__name__))
        return 2


def _key_ok(key):
    return bool(key) and bool(KEY.match(key)) and key == key.lower()


def _key_path(args):
    if not getattr(args, "key", None):
        return None
    store = os.path.abspath(os.path.expanduser(args.store or os.path.join("~", ".grow-pm", "publications")))
    return os.path.join(store, args.key + ".yaml")


def _base(args):
    """(entries, dropped, source) — the record to read or to build on: the key file when it holds one, else the
    note's field (its older fields as entries), else the --carry note's; or an exit code after the result line."""
    kp = _key_path(args)
    if kp and os.path.isfile(kp):
        got = _open(kp, "the key file")
        if isinstance(got, int) or got == "foreign":
            if got == "foreign":
                result(error="the key file's published is not a publication list")
            return 2
        if got[2]:
            e, d = _clean(got[2])
            return e, d, "key"
    for path, what in ((getattr(args, "note", None), "the note"), (getattr(args, "carry", None), "the previous note")):
        if not path or (not os.path.exists(path) and path.lower().endswith((".yaml", ".yml"))):
            continue                                   # a state file not made yet (the first live board)
        got = _open(path, what)
        if isinstance(got, int):
            return got
        if got == "foreign":
            continue
        key = getattr(args, "key", None)
        entries = [e for e in got[2] if not key or e.get("key") in (None, "", key)]   # never another result's mirror
        for lg in _legacy(got[3], got[1]):
            if not any(x.get("surface") == lg["surface"] and x.get("kind") == lg["kind"] for x in entries):
                entries.append(lg)
        if entries:
            e, d = _clean(entries)
            return e, d, "note" if what == "the note" else "carry"
    return [], 0, None


def _matches(e, args):
    return (not getattr(args, "surface", None) or e.get("surface") == args.surface) and \
        (not getattr(args, "kind", None) or e.get("kind") == args.kind) and \
        (not getattr(args, "level", None) or not e.get("level") or e.get("level") == args.level)


def _mirror(note_entries, entries, key, adopted):
    """The note's new list: the other results' entries as they were, this key's in place of its own; entries with no
    key (recorded before keys) give way only when this record was built from them."""
    keep = [e for e in note_entries if e.get("key") and e.get("key") != key] + \
        ([] if adopted else [e for e in note_entries if not e.get("key")])
    return keep + entries


def cmd_find(args):
    if not args.key and not args.note:
        result(error="find needs --key or --note")
        return 2
    if args.key and not _key_ok(args.key):
        result(error="the key is not lower-case words joined by / (at most four parts)")
        return 2
    if args.note and not args.key and os.path.isfile(args.note):
        got = _open(args.note)
        if got == "foreign":
            result(found=[], foreign=True, why="the note's own published property is not a publication list")
            return 0
    got = _base(args)
    if isinstance(got, int):
        return got
    result(found=[e for e in got[0] if _matches(e, args)], source=got[2], **({"dropped": got[1]} if got[1] else {}))
    return 0


def _check_args(args, need_audience=True):
    if args.kind not in KINDS:
        return "the kind is not one of %s" % "|".join(KINDS)
    if not (args.surface in SURFACES or SLUG.match(args.surface or "")):
        return "the surface is not artifact|docs|confluence or a registry id"
    if getattr(args, "level", None) and (args.level not in LEVELS or args.surface != "artifact"):
        return "--level is typed|page, for the artifact surface only"
    if getattr(args, "key", None) and not _key_ok(args.key):
        return "the key is not lower-case words joined by / (at most four parts)"
    if args.surface == "atlassian" and args.kind == "page":
        return "an Atlassian page is Confluence: --surface confluence"
    if args.audience and not (args.audience in ("private", "shared", "unknown") or SPACE.match(args.audience)):
        return "the audience is not private|shared|unknown|space:<KEY> (a personal space is private)"
    if need_audience and not args.audience:
        return "--audience is needed"
    if getattr(args, "at", None) and not AT.match(args.at):
        return "--at is not YYYY-MM-DDTHH:MM[:SS][Z|±HH:MM]"
    if getattr(args, "remote_version", None):
        bad = value_problem("the remote version", args.remote_version, MAX_RV)
        if bad:
            return bad
    if getattr(args, "url", None) is not None:
        return value_problem("the id", args.id) or link_problem(args.url)
    return value_problem("the id", args.id) if getattr(args, "id", None) else None


def _save(args, entries, adopted=False):
    """Write the record: the key file (created when new), then the note's mirror. (exit code, mirror note). A mirror
    that cannot be written is said, never fatal once the key file holds the record."""
    kp, mirror = _key_path(args), None
    if not kp and args.note and args.note.lower().endswith((".yaml", ".yml")) and not os.path.exists(args.note):
        try:                                           # a state file of its own (the first live board): created
            os.makedirs(os.path.dirname(os.path.abspath(args.note)), exist_ok=True)
            with open(args.note, "w", encoding="utf-8") as f:
                f.write("# Written by scripts/publications.py (references/artifact-publishing.md §5)\n")
        except OSError as e:
            result(error="the state file cannot be created: %s" % (e.strerror or type(e).__name__))
            return 1, None
    try:
        if kp:
            if not os.path.isfile(kp):
                os.makedirs(os.path.dirname(kp), exist_ok=True)
                with open(kp, "w", encoding="utf-8") as f:
                    f.write("# Publication record of %s — written by scripts/publications.py "
                            "(references/artifact-publishing.md §5)\n" % args.key)
            got = _open(kp, "the key file")
            if isinstance(got, int) or got == "foreign":
                return 2, None
            write(kp, got[0], got[1], entries)
    except OSError as e:
        result(error="the record cannot be written: %s" % (e.strerror or type(e).__name__))
        return 1, None
    if args.note:
        got = _open(args.note) if os.path.isfile(args.note) or not kp else "missing"
        if got == "missing":
            mirror = "skipped: the note is not there"
        elif got == "foreign":
            mirror = "skipped: the note's own published property is something else"
        elif isinstance(got, int):
            if not kp:
                return got, None
            mirror = "skipped: the note does not read"
        else:
            try:
                write(args.note, got[0], got[1], _mirror(got[2], entries, args.key, adopted) if kp else entries)
                mirror = "written"
            except OSError as e:
                if not kp:
                    result(error="the record cannot be written: %s" % (e.strerror or type(e).__name__))
                    return 1, None
                mirror = "skipped: the note cannot be written"
    return 0, mirror


def cmd_record(args):
    if not args.key and not args.note:
        result(error="record needs --key or --note")
        return 2
    bad = _check_args(args, need_audience=False)
    if bad:
        result(error=bad)
        return 2
    if not args.key and os.path.exists(args.note):
        got = _open(args.note)
        if got == "foreign":
            result(error="the note's own published property is not a publication list — nothing written")
            return 2
        if isinstance(got, int):
            return got
    elif not args.key and not args.note.lower().endswith((".yaml", ".yml")):
        result(error="the note is not there")
        return 2
    base = _base(args)
    if isinstance(base, int):
        return base
    entries, dropped, source = base
    entries = [{k: v for k, v in e.items() if k != "legacy"} for e in entries]
    carried = len(entries) if source == "carry" else 0
    at = args.at or _now()
    if re.match(r"^\d{4}-\d{2}-\d{2}T[\d:]+$", at):
        at += "Z"                                      # a time with no zone is UTC
    same = [e for e in entries if e.get("surface") == args.surface and e.get("kind") == args.kind and
            (not args.level or not e.get("level") or e.get("level") == args.level)]
    entry = next((e for e in same if e.get("id") == args.id), None) or \
        next((e for e in same if _host(e.get("url")) == _host(args.url) and
              (not args.level or e.get("level") == args.level)), None)
    if entry is None:
        if not args.audience:
            result(error="--audience is needed for a place recorded for the first time")
            return 2
        version, entry = 1, {"surface": args.surface, "kind": args.kind}
        entries.append(entry)
    elif entry.get("id") == args.id:
        version = int(entry.get("version") or 1) + 1
    else:                                              # the same place on the same host and level, created anew
        version = 1
        if entry.get("id"):
            entry["replaced"] = list(entry.get("replaced") or []) + [entry["id"]]
    entry.update({"id": args.id, "url": args.url, "version": version, "published": at,
                  "audience": args.audience or entry.get("audience") or "unknown"})
    if args.level:
        entry["level"] = args.level
    if args.key:
        for e in entries:
            e["key"] = args.key
    if args.remote_version:
        entry["remote_version"] = args.remote_version
    else:
        entry.pop("remote_version", None)
    code, mirror = _save(args, entries, adopted=source in ("note", "carry"))
    if code:
        return code
    out = {"recorded": {k: entry[k] for k in FIELDS if k in entry}, "carried": carried}
    if source:
        out["from"] = source
    if dropped:
        out["dropped"] = dropped
    if mirror:
        out["mirror"] = mirror
    result(**out)
    return 0


def cmd_share(args):
    if not args.key and not args.note:
        result(error="share needs --key or --note")
        return 2
    bad = _check_args(args)
    if bad:
        result(error=bad)
        return 2
    base = _base(args)
    if isinstance(base, int):
        return base
    entries = [{k: v for k, v in e.items() if k != "legacy"} for e in base[0]]
    same = [e for e in entries if _matches(e, args) and (not args.id or e.get("id") == args.id)]
    if len(same) != 1:
        result(error="no single recorded place matches — give --id" if same else "no recorded place matches")
        return 2
    same[0]["audience"] = args.audience
    if args.key:
        for e in entries:
            e["key"] = args.key
    code, mirror = _save(args, entries, adopted=base[2] in ("note", "carry"))
    if code:
        return code
    result(shared={k: same[0][k] for k in FIELDS if k in same[0]}, **({"mirror": mirror} if mirror else {}))
    return 0


def cmd_forget(args):
    """The user's «забудь»: one place out of a result's record (the place itself is not touched)."""
    if not args.key:
        result(error="forget needs --key")
        return 2
    if not _key_ok(args.key) or args.kind not in KINDS:
        result(error="the key or the kind is not valid")
        return 2
    base = _base(args)
    if isinstance(base, int):
        return base
    entries = [{k: v for k, v in e.items() if k != "legacy"} for e in base[0]]
    gone = [e for e in entries if _matches(e, args) and (not args.id or e.get("id") == args.id)]
    if len(gone) != 1:
        result(error="no single recorded place matches — give --id" if gone else "no recorded place matches")
        return 2
    entries.remove(gone[0])
    for e in entries:
        e["key"] = args.key
    code, mirror = _save(args, entries, adopted=True)
    if code:
        return code
    result(forgot={k: gone[0][k] for k in ("surface", "kind", "id") if k in gone[0]}, **({"mirror": mirror} if mirror else {}))
    return 0


def cmd_digest(args):
    if not os.path.isfile(args.file):
        result(error="the file is not there")
        return 2
    h, n = hashlib.sha256(), 0
    try:
        with open(args.file, "rb") as f:
            for chunk in iter(lambda: f.read(1 << 20), b""):
                h.update(chunk)
                n += len(chunk)
    except OSError as e:
        result(error="the file does not read: %s" % (e.strerror or type(e).__name__))
        return 2
    result(bytes=n, sha256=base64.b64encode(h.digest()).decode("ascii"))
    return 0


# ------------------------------------------------------------------ check 24
def _ticks(cell):
    return re.findall(r"`([^`]+)`", cell)


def _row(text, field):
    m = re.search(r"^\|\s*`%s`\s*\|(.*?)\|\s*$" % re.escape(field), text, re.M)
    return m.group(1) if m else None


def _first_col(text):
    """The backticked names of a table's first column — `id`, `url` counts both."""
    out = []
    for m in re.finditer(r"^\|([^|]*)\|", text, re.M):
        out += [t for t in _ticks(m.group(1))]
    return out


def _const(src, name):
    m = re.search(r"^%s = \((.*?)\)" % name, src, re.M | re.S)
    return set(re.findall(r'"([^"]+)"', m.group(1))) if m else None


def check_schema(root):
    """Errors for validate-consistency.sh check 24: the kinds, the fixed surfaces, the audiences and the entry fields
    of a publication record must be the same in vault-schema.md, artifact-publishing.md, this script and tools_scan's
    PUBLISHES."""
    errs, texts = [], {}
    for rel in ("references/vault-schema.md", "references/artifact-publishing.md", "scripts/publications.py",
                "scripts/tools_scan.py"):
        try:
            with open(os.path.join(root, rel), encoding="utf-8") as f:
                texts[rel] = f.read()
        except OSError:
            errs.append("%s is missing" % rel)
    if errs:
        return errs
    full, ap, src = texts["references/vault-schema.md"], texts["references/artifact-publishing.md"], \
        texts["scripts/publications.py"]
    sec = re.search(r"#### Publication record.*?(?=\n#### )", full, re.S)
    if not sec:
        return ["vault-schema.md has no «Publication record» section"]
    vs = sec.group(0)
    ctxf = re.search(r"#### Context Fields.*?(?=\n#### )", full, re.S)
    if not ctxf or not re.search(r"^\|\s*`published`\s*\|", ctxf.group(0), re.M):
        errs.append("vault-schema.md: Context Fields has no `published` row")
    want = {"kind": _const(src, "KINDS"), "surface": _const(src, "SURFACES"), "audience": _const(src, "AUDIENCES"),
            "field": _const(src, "FIELDS"), "level": _const(src, "LEVELS")}
    if None in want.values():
        return ["scripts/publications.py: KINDS, SURFACES, AUDIENCES, FIELDS or LEVELS not found"]
    got = {"kind": set(_ticks(_row(vs, "kind") or "")),
           "surface": {t for part in (_row(vs, "surface") or "").split("·")
                       for t in _ticks(part) if part.strip().startswith("`") and len(_ticks(part)) == 1},
           "audience": set(_ticks(_row(vs, "audience") or "")),
           "field": set(_first_col(vs)),
           "level": set(_ticks((_row(vs, "level") or "").split("—")[0]))}
    for k in want:
        if got[k] != want[k]:
            errs.append("vault-schema.md: the %s values %s ≠ publications.py %s" % (
                k, "|".join(sorted(got[k])), "|".join(sorted(want[k]))))
    s1 = re.search(r"## 1\. The kind of result(.*?)\n## ", ap, re.S)
    kinds_ap = set(re.findall(r"^\|\s*`([a-z]+)`\s*\|", s1.group(1), re.M)) if s1 else set()
    if kinds_ap != want["kind"]:
        errs.append("artifact-publishing.md §1: the kinds %s ≠ publications.py %s" % (
            "|".join(sorted(kinds_ap)), "|".join(sorted(want["kind"]))))
    s5 = re.search(r"## 5\. Publish and record(.*?)\n## ", ap, re.S)
    body5 = s5.group(1) if s5 else ""
    surf = (_row(body5, "surface") or "").split("the id of")[0]
    if set(_ticks(surf)) != want["surface"]:
        errs.append("artifact-publishing.md §5: the surfaces %s ≠ publications.py %s" % (
            "|".join(sorted(set(_ticks(surf)))), "|".join(sorted(want["surface"]))))
    aud = set(_ticks((_row(body5, "audience") or "").split("—")[0]))
    if aud != want["audience"]:
        errs.append("artifact-publishing.md §5: the audiences %s ≠ publications.py %s" % (
            "|".join(sorted(aud)), "|".join(sorted(want["audience"]))))
    tbl = re.search(r"\| Field \| What \|.*?(?=\n\n)", body5, re.S)
    fields_ap = set(_first_col(tbl.group(0))) - {"Field"} if tbl else set()
    if fields_ap != want["field"]:
        errs.append("artifact-publishing.md §5: the entry fields %s ≠ publications.py %s" % (
            "|".join(sorted(fields_ap)), "|".join(sorted(want["field"]))))
    pubs = _const(texts["scripts/tools_scan.py"], "PUBLISHES")
    if pubs != want["kind"]:
        errs.append("tools_scan.py PUBLISHES %s ≠ publications.py KINDS %s" % (
            "|".join(sorted(pubs or ())), "|".join(sorted(want["kind"]))))
    return errs


def main(argv=None):
    ap = argparse.ArgumentParser(prog="publications.py", description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd")
    def common(p):
        p.add_argument("--key", help="the result's key, e.g. design-bridge/zorg/new-delivery-feature")
        p.add_argument("--note", help="the note the run saved (or a YAML state file): read when there is no key "
                                      "file, and given the record as its `published` field")
        p.add_argument("--store", help="the folder of the key files (default ~/.grow-pm/publications)")
        p.add_argument("--carry", help="an older note of the same result, read when neither holds a record")
        return p
    p = common(sub.add_parser("find"))
    p.add_argument("--surface")
    p.add_argument("--kind")
    p.add_argument("--level", choices=LEVELS)
    p = common(sub.add_parser("record"))
    p.add_argument("--surface", required=True, help="artifact | docs | confluence | a tools-registry id")
    p.add_argument("--kind", required=True, help="|".join(KINDS))
    p.add_argument("--level", help="typed | page — an ARTIFACT's level")
    p.add_argument("--id", required=True)
    p.add_argument("--url", required=True, help="the place's link, without credentials")
    p.add_argument("--audience", help="private | shared | unknown | space:<KEY>; a new version keeps the place's own")
    p.add_argument("--remote-version", help="the place's own version or revision, when its tool gives one")
    p.add_argument("--at", help="the version's time (default now, UTC)")
    p = common(sub.add_parser("share"))
    p.add_argument("--surface", required=True)
    p.add_argument("--kind", required=True)
    p.add_argument("--level", choices=LEVELS)
    p.add_argument("--id")
    p.add_argument("--audience", required=True)
    p = common(sub.add_parser("forget"))
    p.add_argument("--surface", required=True)
    p.add_argument("--kind", required=True)
    p.add_argument("--level", choices=LEVELS)
    p.add_argument("--id")
    p = sub.add_parser("digest")
    p.add_argument("file")
    args = ap.parse_args(argv)
    fn = {"find": cmd_find, "record": cmd_record, "share": cmd_share, "forget": cmd_forget,
          "digest": cmd_digest}.get(args.cmd)
    if fn is None:
        ap.print_help()
        return 2
    return fn(args)


if __name__ == "__main__":
    sys.exit(main())
