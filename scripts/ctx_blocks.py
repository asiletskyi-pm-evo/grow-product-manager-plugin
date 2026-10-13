#!/usr/bin/env python3
"""Grow PM — a repository's managed regions in the context records, the class of each block, and what the store
remembers of them (since v3.13.0).

A repository's block lives in the user's context as a managed region inside some record's body:

    <!-- <ns>:begin id=<block> v=<version> -->
    ...
    <!-- <ns>:end id=<block> -->

optionally inside a section wrapper (`<!-- <ns>:section:begin -->` … `<!-- <ns>:section:end -->`, which is not a
block itself). A block that "mine" holds is found here; the same block that "theirs" publishes comes from
`ctx_repos.fetch`, and `classify` says what the two (and the base the state remembers) mean for the plan.

The pure part reads nothing and writes nothing:

- norm          the text two blocks are compared by (and hashed by)
- find_regions  {block id: {host, text, v}} of one namespace over all records, and the structure errors
- classify      the plan's sign for one block from mine / theirs / the state

The persistent part is the store's memory of a repository, under `<store>/.state/blocks/` — snapshots keep it, so
`ctx undo` brings it back:

- load_state / save_state   `<repo>.json`: when and where the repository was last checked, and per block the hash
                            of its base, the last ten bases, the version, the host record, the time it was checked
                            and whether you removed it
- put_base / get_base       `<repo>/<sha>.md`: the text of a base as it was stored, named by the hash of its
                            normalised form (a hash is cs.sha_text(norm(text)))
- prune_bases               drop the base texts no block refers to any more
- last_checked              read-only, never raises: the time of the last check, for the session digest

Every write goes through ctx_store.atomic_write / check_target (the write allow-list). A repository id is
kebab-case and nothing else, so it can never name a path outside `.state/blocks/`.

`find_regions` is the strict reading of the user's own records. `ctx_repos._regions` is the lenient reading of
what a repository publishes (it keeps the first of a repeated id and skips what is never closed); the two differ
on purpose and share only the marker grammar. Stdlib only.
"""
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ctx_store as cs  # noqa: E402

ID = r"[A-Za-z0-9_.-]+"
BEGIN_ATTRS = re.compile(r"^\s+id=(%s)((?:\s.*)?)$" % ID, re.S)     # what follows `<ns>:begin` in a well-formed marker
END_ATTRS = re.compile(r"^\s+id=(%s)\s*$" % ID)                      # …and what follows `<ns>:end`
VERSION = re.compile(r"(?:^|\s)v=([^\s>]+)")
ANY_ID = re.compile(r"id=(%s)" % ID)


def norm(text):
    """CRLF → LF, no trailing spaces or tabs on a line, no trailing blank lines. None is the empty text."""
    lines = (text or "").replace("\r\n", "\n").split("\n")
    return "\n".join(line.rstrip(" \t\r") for line in lines).rstrip("\n")


def _scan(text, ns):
    """([(id, start, end, v)] of the sound regions of `ns` in `text`, [(pos, id, why)] of the broken ones).

    Every marker of the namespace is read, well-formed or not (a begin or an end that does not parse is a broken
    marker). A begin opens a region on a stack; an end closes the nearest open region with its id. A region is
    sound when it is closed by its own end and nothing opened or ended inside it: a begin met while another is open
    marks both nested; a begin never closed, an end with no begin, and an end whose id differs from every open
    begin are broken markers (an unclosed begin is "broken marker" even when it was also nested).
    """
    rx = re.compile(r"<!--\s*%s:(begin|end)(?![A-Za-z0-9_:.])([^>]*)-->" % re.escape(ns))
    regions, errors, stack = [], [], []
    for mo in rx.finditer(text):
        kind, attrs = mo.group(1), mo.group(2)
        parsed = (BEGIN_ATTRS if kind == "begin" else END_ATTRS).match(attrs)
        if not parsed:
            guess = ANY_ID.search(attrs)
            errors.append((mo.start(), guess.group(1) if guess else "", "broken marker"))
            continue
        bid = parsed.group(1)
        if kind == "begin":
            version = VERSION.search(parsed.group(2))
            op = {"id": bid, "start": mo.start(), "v": version.group(1) if version else "", "bad": None}
            if stack:
                for o in stack + [op]:
                    o["bad"] = o["bad"] or "nested"
            stack.append(op)
            continue
        at = next((i for i in range(len(stack) - 1, -1, -1) if stack[i]["id"] == bid), None)
        if at is None:
            errors.append((mo.start(), bid, "broken marker"))
            continue
        closed, lost = stack[at], stack[at + 1:]
        del stack[at:]
        for o in lost:                                  # begun inside it and never ended
            errors.append((o["start"], o["id"], "broken marker"))
        if closed["bad"]:
            errors.append((closed["start"], bid, closed["bad"]))
        else:
            regions.append((bid, closed["start"], mo.end(), closed["v"]))
    for o in stack:                                     # still open at the end of the text
        errors.append((o["start"], o["id"], "broken marker"))
    return regions, errors


def find_regions(records, ns):
    """({block id: {"host": record id, "text": the whole region, markers included, no final newline, "v": version}},
    [{"block", "host", "why"}]) for the regions of namespace `ns` over `records` (dicts with `id` and `body`).

    Other namespaces are ignored. Regions inside the `<ns>:section` wrapper are found; the wrapper is not a block.
    `why` is "duplicate" (the id is met again, in this or another record: every occurrence after the first is
    reported, in record order), "broken marker" (a begin without its end, an end without its begin, an end whose
    id differs, a marker that does not parse) or "nested" (a region begins inside another one; the outer and the
    inner are both reported). `v` is "" when the marker carries none.

    A block id that appears in any error is left out of the result, so a caller that plans from the result never
    touches a block it was told is broken; the errors say which ids those are. A marker too broken to name an
    id is reported with block "".
    """
    found, bad, errors = {}, set(), []
    for rec in records:
        host, body = rec.get("id"), rec.get("body") or ""
        regions, broken = _scan(body, ns)
        events = [(start, "region", (bid, start, end, v)) for bid, start, end, v in regions]
        events += [(pos, "error", (bid, why)) for pos, bid, why in broken]
        for _, kind, item in sorted(events, key=lambda e: e[0]):
            if kind == "error":
                bid, why = item
            else:
                bid, start, end, v = item
                if bid not in found:
                    found[bid] = {"host": host, "text": body[start:end], "v": v}
                    continue
                why = "duplicate"
            errors.append({"block": bid, "host": host, "why": why})
            if bid:
                bad.add(bid)
    return {k: v for k, v in found.items() if k not in bad}, errors


def classify(mine, theirs, st):
    """The plan's sign for one block. `mine` / `theirs`: the region text on either side, or None when absent.
    `st`: what the state remembers of the block, {"base_sha", "bases", "user_removed"}, or None when there is no
    base. `bases` holds hashes of recent versions (never their text); a hash is cs.sha_text(norm(text)).

    The rules apply in this order:
      "="  both are present and equal once normalised (even with no base)
      "+"  yours is absent and there never was a base: a new block
      "✂"  yours is absent and there is a base: you removed it (flagged or not)
      "−"  the repository's is absent and yours is there: the repository removed the block
      "?"  both are present, differ, and there is no base to tell which moved
      "~"  yours is the base (or an older base): the repository moved on, take it
      "✎"  theirs is the base (or an older base): only you changed it, keep it
      "⚠"  neither is a base: both changed

    Skipped blocks never come here. With neither side present and no base there is no block to speak of (ValueError).
    """
    if mine is None and theirs is None and st is None:
        raise ValueError("classify needs a block: neither mine nor theirs is present, and there is no base")
    nm = None if mine is None else norm(mine)
    nt = None if theirs is None else norm(theirs)
    if nm is not None and nt is not None and nm == nt:
        return "="
    if nm is None:
        return "+" if st is None else "✂"
    if nt is None:
        return "−"
    if st is None:
        return "?"
    known = set(st.get("bases") or ())
    if st.get("base_sha"):
        known.add(st["base_sha"])
    if cs.sha_text(nm) in known:
        return "~"
    if cs.sha_text(nt) in known:
        return "✎"
    return "⚠"


# ------------------------------------------------------------------ the store's memory of a repository
REPO_ID = re.compile(r"[a-z0-9][a-z0-9-]*")
SHA = re.compile(r"[0-9a-f]{64}")
BASE_FILE = re.compile(r"[0-9a-f]{64}\.md")
MAX_BASES = 10                                  # the hashes of the last ten bases are kept, the oldest dropped first


def _repo(repo_id):
    """The repository id when it is kebab-case, else StoreError: it names a folder and a file under `.state/blocks/`."""
    if not isinstance(repo_id, str) or not REPO_ID.fullmatch(repo_id):
        raise cs.StoreError("not a repository id (lower-case letters, digits and '-'): %.60r" % (repo_id,))
    return repo_id


def _state_path(store, repo_id):
    return os.path.join(store.state_dir, "blocks", _repo(repo_id) + ".json")


def _bases_dir(store, repo_id):
    return os.path.join(store.state_dir, "blocks", _repo(repo_id))


def _clean(state, where):
    """A copy of `state` in its stored shape: every key present, `v` a string ("" is unknown), `bases` without
    repeats, the last MAX_BASES of them with `base_sha` the newest. A wrong shape → StoreError naming `where`."""
    if not isinstance(state, dict):
        raise cs.StoreError("%s: the state is not an object" % where)
    blocks = state.get("blocks")
    if blocks is None:
        blocks = {}
    if not isinstance(blocks, dict):
        raise cs.StoreError("%s: blocks is not an object" % where)
    out_blocks = {}
    for bid, block in blocks.items():
        if not isinstance(block, dict):
            raise cs.StoreError("%s: block %s is not an object" % (where, bid))
        bases, base_sha = block.get("bases"), block.get("base_sha")
        if bases is None:
            bases = []
        if not isinstance(bases, list) or not all(isinstance(h, str) for h in bases):
            raise cs.StoreError("%s: bases of block %s are not a list of hashes" % (where, bid))
        if base_sha is not None and not isinstance(base_sha, str):
            raise cs.StoreError("%s: base_sha of block %s is not a hash" % (where, bid))
        seq = list(bases) + ([base_sha] if base_sha else [])
        kept = []
        for h in reversed(seq):                  # a hash stays once, at its newest place
            if h not in kept:
                kept.append(h)
        b = dict(block)
        b["bases"] = kept[:MAX_BASES][::-1]
        b["base_sha"] = base_sha or None
        b["v"] = block.get("v") or ""
        b.setdefault("host", None)
        b.setdefault("checked", None)
        b.setdefault("user_removed", False)
        out_blocks[bid] = b
    out = dict(state)
    out["blocks"] = out_blocks
    for key in ("checked", "source", "version"):
        out.setdefault(key, None)
    return out


def load_state(store, repo_id):
    """What the store remembers of a repository: {"checked", "source", "version", "blocks": {block id: {"base_sha",
    "bases", "v", "host", "checked", "user_removed"}}}. A repository with no state file gives the empty state; a
    state file that cannot be read or is not valid → StoreError naming it (it is never reset silently)."""
    path = _state_path(store, repo_id)
    where = ".state/blocks/%s.json" % repo_id
    if not os.path.lexists(path):
        return _clean({}, where)
    try:
        raw = cs.read_text(path)
    except FileNotFoundError:
        return _clean({}, where)
    except (OSError, UnicodeDecodeError) as e:
        raise cs.StoreError("state not readable: %s (%s)" % (where, e))
    try:
        data = json.loads(raw)
    except ValueError as e:
        raise cs.StoreError("state not valid: %s (%s)" % (where, e))
    return _clean(data, where)


def save_state(store, repo_id, state):
    """Write the repository's state (sorted, indented, atomic). `bases` are kept to the last ten with `base_sha`
    the newest of them, as `load_state` gives them back."""
    path = _state_path(store, repo_id)
    clean = _clean(state, ".state/blocks/%s.json" % repo_id)
    try:
        text = json.dumps(clean, ensure_ascii=False, indent=1, sort_keys=True) + "\n"
    except (TypeError, ValueError) as e:
        raise cs.StoreError("state not storable: .state/blocks/%s.json (%s)" % (repo_id, e))
    cs.atomic_write(path, text)


def put_base(store, repo_id, text):
    """Keep `text` (None is empty) as it is, byte for byte, as a base of the repository; the hash of its normalised
    form names it and is returned. A base that is already there is not written again."""
    folder = _bases_dir(store, repo_id)
    sha = cs.sha_text(norm(text))
    path = os.path.join(folder, sha + ".md")
    if not os.path.isfile(path):
        cs.atomic_write(path, text or "")
    return sha


def get_base(store, repo_id, sha):
    """The text kept under `sha` as it was stored, or None (no such base; `sha` is not a hash)."""
    folder = _bases_dir(store, repo_id)
    if not isinstance(sha, str) or not SHA.fullmatch(sha):
        return None
    path = os.path.join(folder, sha + ".md")
    if not os.path.isfile(path):
        return None
    try:
        return cs.read_text(path)
    except FileNotFoundError:
        return None
    except (OSError, UnicodeDecodeError) as e:
        raise cs.StoreError("base not readable: .state/blocks/%s/%s.md (%s)" % (repo_id, sha, e))


def prune_bases(store, repo_id, state):
    """Remove the base texts of the repository whose hash is no block's `base_sha` or among its `bases` (as
    `save_state` would keep them: the last ten). Other files in the folder are left alone. Returns the removed hashes."""
    folder = _bases_dir(store, repo_id)
    keep = set()
    for block in _clean(state, ".state/blocks/%s.json" % repo_id)["blocks"].values():
        keep.update(block["bases"])
    removed = []
    for name in sorted(os.listdir(folder)) if os.path.isdir(folder) else []:
        path = os.path.join(folder, name)
        if BASE_FILE.fullmatch(name) and name[:-3] not in keep and os.path.isfile(path):
            cs.check_target(path)
            os.remove(path)
            removed.append(name[:-3])
    return removed


def last_checked(store_root, repo_id):
    """When the repository was last checked (the state's `checked`), or None. Read-only, and never raises — a state
    that is missing, unreadable or not valid is None — for the session digest."""
    try:
        checked = load_state(cs.Store(store_root), repo_id)["checked"]
    except Exception:  # noqa: BLE001 — a digest must not fail over a state file
        return None
    return checked if isinstance(checked, str) and checked else None
