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
- is_rule       does the repository's begin marker say `policy=rule` (a core rule, since v3.14.0)

The persistent part is the store's memory of a repository, under `<store>/.state/blocks/` — snapshots keep it, so
`ctx undo` brings it back:

- load_state / save_state   `<repo>.json`: when and where the repository was last checked, and per block the hash
                            of its base, the last ten bases, the version, the host record, the time it was checked
                            and whether you removed it; since v3.14.0 also `rejected`, the repository texts you
                            rejected by undoing a sync pass (the last ten hashes per block)
- put_base / get_base       `<repo>/<sha>.md`: the text of a base as it was stored, named by the hash of its
                            normalised form (a hash is cs.sha_text(norm(text)))
- prune_bases               drop the base texts no block refers to any more
- last_checked              read-only, never raises: the time of the last check, for the session digest

And the first use of it, for a context that already holds a repository's blocks:

- adopt                     the initial base of every block of the repository that is in the context (spec B5):
                            "base" (yours is the repository's), "edit" (the same version, yours differs: the
                            repository's text is the base and yours counts as your edit), "none" (another version, or
                            the repository does not offer it: no base, the plan shows "?"). Only the state and the
                            base texts are written (after a snapshot); the records and the compiled copies never.

And the second, which only reads:

- plan                      one table per repository: the sign of every block (spec B5/B6), the records an apply
                            without decisions would rewrite, the questions it would ask. Nothing is written, no
                            lock is taken. `render_plan` is its text; `base_version` the version it speaks of.

And the third, which writes your records:

- apply                     one pass of the plan (spec B6/B7): what needs no answer is applied, your edits stay,
                            a "⚠" / "?" waits for its answer (theirs | mine | both) and a "+" for --add; one
                            snapshot, the host records, the state, one journal line, the compile. A pass that
                            changes nothing writes only the time of the check. `render_apply` is its text.

Every write goes through ctx_store.atomic_write / check_target (the write allow-list). A repository id is
kebab-case of at most 64 characters and nothing else, so it can never name a path outside `.state/blocks/`.

`find_regions` is the strict reading of the user's own records. `ctx_repos._regions` is the lenient reading of
what a repository publishes (it keeps the first of a repeated id); the two differ on purpose and share only the
marker grammar. A published file with no region of the namespace or with a begin never closed is refused before it
is read (`ctx_repos._unsound`), and one that holds none of the blocks you have a base for is refused by `plan`
(SourceLost): neither is ever read as "the repository removed every block". Stdlib only.
"""
import collections
import copy
import difflib
import json
import os
import re
import sys
import urllib.parse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ctx_common as cc  # noqa: E402
import ctx_overlay as ov  # noqa: E402
import ctx_ops as co  # noqa: E402
import ctx_read as cr  # noqa: E402
import ctx_store as cs  # noqa: E402

ID = r"[A-Za-z0-9_.-]+"
BEGIN_ATTRS = re.compile(r"^\s+id=(%s)((?:\s.*)?)$" % ID, re.S)     # what follows `<ns>:begin` in a well-formed marker
END_ATTRS = re.compile(r"^\s+id=(%s)\s*$" % ID)                      # …and what follows `<ns>:end`
VERSION = re.compile(r"(?:^|\s)v=([^\s>]+)")
ANY_ID = re.compile(r"id=(%s)" % ID)
LEADING_BEGIN = re.compile(r"\s*<!--\s*[^\s:>]+:begin(?![A-Za-z0-9_:.])([^>]*)-->")   # the begin marker a region text starts with
RULE_WORD = re.compile(r"(?:^|\s)policy=rule(?:\s|$)")


def norm(text):
    """CRLF → LF, no trailing spaces or tabs on a line, no trailing blank lines. None is the empty text."""
    lines = (text or "").replace("\r\n", "\n").split("\n")
    return "\n".join(line.rstrip(" \t\r") for line in lines).rstrip("\n")


def is_rule(region_text):
    """Does the repository hold this block as a core rule? True when the attributes of the begin marker the region text
    starts with — what follows its id — hold the whole word `policy=rule` (`<!-- <ns>:begin id=<id> v=<v> policy=rule -->`).
    Text inside the region never counts; None, "" and a text that does not start with a well-formed begin marker are no
    rule. It is read from the repository's text (theirs), never from yours."""
    found = LEADING_BEGIN.match(region_text or "")
    attrs = BEGIN_ATTRS.match(found.group(1)) if found else None
    return bool(attrs and RULE_WORD.search(attrs.group(2)))


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


def classify(mine, theirs, st, lagging=False):
    """The plan's sign for one block. `mine` / `theirs`: the region text on either side, or None when absent.
    `st`: what the state remembers of the block, {"base_sha", "bases", "v", "user_removed"}, or None when there is no
    base. `bases` holds hashes of recent versions (never their text); a hash is cs.sha_text(norm(text)). `lagging`
    (since v3.14.0): the source's copy is known to lag behind your bases (`source_lags`: a block it carries is at an
    older `v=` than your base of it, and none at a newer one) — `plan` says so for the whole copy.

    The rules apply in this order:
      "="  both are present and equal once normalised (even with no base)
      "+"  yours is absent and there never was a base: a new block
      "✂"  yours is absent and there is a base: you removed it (flagged or not)
      the repository's is absent and yours is there — the repository removed the block:
      "?"    there is no base: nothing says yours is the repository's text
      unless the source's copy lags (`lagging`, `behind`): a copy older than your bases cannot tell a removal
      "="    …yours is the base (or an older base): nothing moves
      "✎"    …you changed it: your edit stays, nothing moves
      "−"    yours is the base (or an older base): you never changed it, remove it
      "⚠"    yours is no base: you changed it — your edit is not dropped without a question
      "?"  both are present, differ, and there is no base to tell which moved
      "="  yours is the base and theirs an older base: the source lags behind yours (`behind`) — nothing moves
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
    if st is None:
        return "?"
    known = set(st.get("bases") or ())
    if st.get("base_sha"):
        known.add(st["base_sha"])
    if nt is None:
        if behind(mine, None, st, lagging):
            return "=" if cs.sha_text(nm) in known else "✎"
        return "−" if cs.sha_text(nm) in known else "⚠"
    if behind(mine, theirs, st):
        return "="
    if cs.sha_text(nm) in known:
        return "~"
    if cs.sha_text(nt) in known:
        return "✎"
    return "⚠"


VERSION_NUMBER = re.compile(r"[vV]?(\d{1,9}(?:[.-]\d{1,9}){0,7})")     # 0.4, v3.14.0, 2026-10-16 — a version that orders


def _version_key(v):
    """The version `v` as numbers to compare (1.0 and 1 are the same), or None when it is not dotted or dashed digits."""
    found = VERSION_NUMBER.fullmatch(v.strip()) if isinstance(v, str) else None
    if not found:
        return None
    parts = [int(x) for x in re.split(r"[.-]", found.group(1))]
    while len(parts) > 1 and parts[-1] == 0:
        parts.pop()
    return tuple(parts)


def _older(a, b):
    """Is version `a` older than version `b`? False when either is unknown or is no version that orders."""
    ka, kb = _version_key(a), _version_key(b)
    return ka is not None and kb is not None and ka < kb


def behind(mine, theirs, st, lagging=False):
    """Does the source lag behind your base of a block? A copy of the source that lags (an MCP mirror not updated yet,
    a folder restored from a backup) would otherwise read as "the repository moved" — an apply would take your block a
    version back, or remove a block the copy does not have yet. Two cases:
      - it offers an older base of a block whose base yours is;
      - it does not offer a block you hold a base for, and the copy as a whole is known to lag (`lagging`, see
        `source_lags`), since v3.14.0: a block added after that copy was made is not in it, which is no removal.
    The plan says "=" with a note ("✎" for a block you edited that the copy lacks) and apply writes nothing: the base
    stays."""
    if mine is None or not st or not st.get("base_sha"):
        return False
    if theirs is None:
        return bool(lagging)
    nm, nt = norm(mine), norm(theirs)
    if nm == nt:
        return False
    sm, sh = cs.sha_text(nm), cs.sha_text(nt)
    return sm == st["base_sha"] and sh != st["base_sha"] and sh in set(st.get("bases") or ())


def source_lags(state, fetched, skip=()):
    """Does the source's copy lag behind your bases — on positive evidence only (since v3.14.0)? Among the blocks the
    copy's blocks file carries (`fetched["blocks"]`; neither a skipped block nor a team block the core folder builds, on
    either side), at least one is at an older `v=` than your base of it (the state's `v`), and none is at a newer one.
    Blocks with no base, with the same version, or with a version that does not order (`_version_key`) say nothing. A
    core whose blocks carry their own versions is never "behind" for a block it removed while the others stay: the
    evidence is in the blocks it still carries."""
    built = fetched.get("team") is not None or bool(fetched.get("team_error"))
    older = newer = False
    for bid, text in (fetched.get("blocks") or {}).items():
        entry = (state.get("blocks") or {}).get(bid)
        if bid in skip or (bid == "team" and built) or not entry or not (entry.get("base_sha") or entry.get("bases")):
            continue
        theirs_v, yours_v = _marker_version(text), entry.get("v")
        older = older or _older(theirs_v, yours_v)
        newer = newer or _older(yours_v, theirs_v)
    return older and not newer


# ------------------------------------------------------------------ the store's memory of a repository
REPO_ID = re.compile(r"[a-z0-9][a-z0-9-]{0,63}")         # at most 64 characters (since v3.14.0): it names a file and a folder
SHA = re.compile(r"[0-9a-f]{64}")
BASE_FILE = re.compile(r"[0-9a-f]{64}\.md")
MAX_BASES = 10                                  # the hashes of the last ten bases are kept, the oldest dropped first
MAX_REJECTED = 10                               # the repository texts you rejected, per block: the last ten, the oldest dropped first
REMOVED = "removed"                             # what stands for "the repository removed the block" where a text's hash would


def _repo(repo_id):
    """The repository id when it is kebab-case of at most 64 characters, else StoreError: it names a folder and a file
    under `.state/blocks/`."""
    if not isinstance(repo_id, str) or not REPO_ID.fullmatch(repo_id):
        raise cs.StoreError("not a repository id (lower-case letters, digits and '-', at most 64): %.60r" % (repo_id,))
    return repo_id


def _state_path(store, repo_id):
    return os.path.join(store.state_dir, "blocks", _repo(repo_id) + ".json")


def _bases_dir(store, repo_id):
    return os.path.join(store.state_dir, "blocks", _repo(repo_id))


def _newest(seq, limit):
    """`seq` with every value once, at its newest (last) place, and only the last `limit` of them, oldest first."""
    kept = []
    for h in reversed(seq):
        if h not in kept:
            kept.append(h)
    return kept[:limit][::-1]


def _clean(state, where):
    """A copy of `state` in its stored shape: every key present, `v` a string ("" is unknown), `bases` without
    repeats, the last MAX_BASES of them with `base_sha` the newest. Unknown top-level keys are kept as they are, except
    `rejected` ({block: [sha | "removed", …]}: the repository texts you rejected by undoing a sync pass, oldest first),
    which is kept to the last MAX_REJECTED values per block without repeats, and left out when absent or null. A wrong
    shape → StoreError naming `where`."""
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
        b = dict(block)
        b["bases"] = _newest(list(bases) + ([base_sha] if base_sha else []), MAX_BASES)   # a hash stays once, at its newest place
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
    rejected = out.pop("rejected", None)
    if rejected is not None:
        if not isinstance(rejected, dict):
            raise cs.StoreError("%s: rejected is not an object" % where)
        for bid, seq in rejected.items():
            if not isinstance(seq, list) or not all(isinstance(h, str) for h in seq):
                raise cs.StoreError("%s: rejected texts of block %s are not a list of hashes" % (where, bid))
        out["rejected"] = {bid: _newest(seq, MAX_REJECTED) for bid, seq in rejected.items()}
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
    the newest of them, as `load_state` gives them back. Since v3.14.0 it also clears what a write cut short left: the
    temp files (`.<name>.tmp`) older than 24 h in `.state/blocks/` and in the repository's bases folder
    (`cs.remove_stale_tmp`; never a reason to fail)."""
    path = _state_path(store, repo_id)
    clean = _clean(state, ".state/blocks/%s.json" % repo_id)
    try:
        text = json.dumps(clean, ensure_ascii=False, indent=1, sort_keys=True) + "\n"
    except (TypeError, ValueError) as e:
        raise cs.StoreError("state not storable: .state/blocks/%s.json (%s)" % (repo_id, e))
    cs.atomic_write(path, text)
    for folder in (os.path.dirname(path), _bases_dir(store, repo_id)):
        cs.remove_stale_tmp(folder)


def put_base(store, repo_id, text):
    """Keep `text` (None is empty) as it is, byte for byte, as a base of the repository; the hash of its normalised
    form names it and is returned. A base that is already there is not written again. Anything else that is not text
    (a number, bytes, a list …) → StoreError, nothing written (since v3.14.0)."""
    folder = _bases_dir(store, repo_id)
    if text is not None and not isinstance(text, str):
        raise cs.StoreError("a base is text, not %s: .state/blocks/%s/" % (type(text).__name__, repo_id))
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


# ------------------------------------------------------------------ adopt
def _marker_version(text):
    """The `v=` of the begin marker of a region text; "" when it carries none."""
    found = VERSION.search((text or "").split("-->", 1)[0])
    return found.group(1) if found else ""


def _initial_base(mine, theirs):
    """(outcome, why) for one block that is in the context (`mine`, a region text) and has no base yet.

    `theirs` is the repository's region text, or None when it does not offer the block. The version is part of the
    region text (the begin marker), so equal texts have equal versions. The rules (spec B5):
      "base"  the texts are equal once normalised: yours is the repository's
      "edit"  the same known version and different texts: the repository's text is the base, yours is your edit
      "none"  the repository does not offer it; another version; or a version nobody knows and different texts
              (nothing says which of the two moved)
    """
    if theirs is None:
        return "none", "the repository does not offer this block"
    vm, vt = _marker_version(mine), _marker_version(theirs)
    if norm(mine) == norm(theirs):
        return "base", "same as the repository's%s" % (" (v=%s)" % vt if vt else "")
    if vm and vm == vt:
        return "edit", ("same version (v=%s), your text differs: the repository's text is the base, yours is your edit" % vm)
    if vm and vt:
        return "none", "another version (yours v=%s, the repository's v=%s)" % (vm, vt)
    return "none", "version unknown (yours %s, the repository's %s) and the texts differ" % (vm or "—", vt or "—")


def adopt(store, copies, home, repo, fetched, now, apply):
    """The initial bases of the blocks of `repo` that are already in the context, from `fetched` (what
    `ctx_repos.fetch` returned, with no `error`).

    Returns {"repo": id, "blocks": {block id: "base" | "edit" | "none" | "has-base"}, "why": {block id: text},
    "new": [ids the repository offers and the context lacks: the plan shows "+"], "problems": [find_regions errors:
    the blocks left out because their regions are broken], "written": bool, "snapshot": folder or None}.
    "has-base" is a block whose state entry holds a base: it is left exactly as it is, so adopting again never
    hides an edit (an entry with no base, such as a removal mark on a region you have put back, gets one). A block of `skip_blocks` is not part of it. The repository's `team` region is the block "team"
    (a failed team build, `team_error`, gives "none"); every other block comes from `fetched["blocks"]`.

    Without `apply` nothing is written. With it, and when some block gets a base: a snapshot (labelled adopt), then
    the base texts, then the state (checked, source and an entry per adopted block: the hash of the base, its
    version, the record holding the region, when it was checked, nothing removed), then the base texts nobody refers
    to are pruned, then one journal line `provider-adopt`. The records and the compiled copies are never written here;
    the caller holds the lock and has imported the edits waiting first (`ctx provider adopt --apply` does, as every
    writing command does), so the snapshot holds them and `ctx undo` never takes them back with the adopt. A crash
    after the texts leaves orphan base texts and no state.
    """
    if fetched.get("error"):
        raise ValueError("adopt needs a repository that was fetched, not one that failed: %s" % fetched["error"])
    rid, skip = repo["id"], set(repo.get("skip_blocks") or ())
    mine, problems = find_regions(store.load(), namespace_of(repo, fetched))
    theirs = dict(fetched.get("blocks") or {})
    if fetched.get("team") is not None:
        theirs["team"] = fetched["team"]
    team_error = fetched.get("team_error")
    state = load_state(store, rid)
    checked = fetched.get("checked") or now
    blocks, why, entries, texts = {}, {}, {}, {}
    for bid, found in mine.items():
        if bid in skip:
            continue
        held = state["blocks"].get(bid) or {}
        if held.get("base_sha") or held.get("bases"):
            blocks[bid], why[bid] = "has-base", "already has a base — left as it is"
        elif bid == "team" and team_error:
            blocks[bid], why[bid] = "none", team_error
        else:
            blocks[bid], why[bid] = _initial_base(found["text"], theirs.get(bid))
            if blocks[bid] in ("base", "edit"):
                texts[bid] = theirs[bid]
                entries[bid] = {"v": _marker_version(theirs[bid]), "host": found["host"], "checked": checked,
                                "user_removed": None}
    left_out = {x["block"] for x in problems}
    new = [bid for bid in theirs if bid not in mine and bid not in left_out and bid not in skip and bid not in state["blocks"]]
    res = {"repo": rid, "blocks": blocks, "why": why, "new": new, "problems": problems, "written": False, "snapshot": None}
    if not apply or not entries:
        return res
    snap = co.snapshot(store, copies, home, "adopt")
    for bid, text in texts.items():
        sha = put_base(store, rid, text)
        state["blocks"][bid] = dict(entries[bid], base_sha=sha, bases=[sha])
    state["checked"], state["source"] = checked, fetched.get("source")
    save_state(store, rid, state)
    prune_bases(store, rid, state)
    store.journal({"ts": now, "op": "provider-adopt", "source": "repo:" + rid, "ids": list(entries), "snapshot": snap})
    res.update(written=True, snapshot=snap)
    return res


# ------------------------------------------------------------------ plan
SKIPPED = "·"                                   # not a decision: a block the registration skips, or a team block that cannot be built
HEADER_CLIP, NOTE_CLIP, LINE_CLIP, DIFF_LINES = 80, 300, 120, 3
CONTROLS = cc.CONTROLS                  # one definition for what is printed from a server (ctx_common)
MARKER_LINE = re.compile(r"^\s*<!--\s*[^\s:>]+:(?:begin|end)(?![A-Za-z0-9_:.])[^>]*-->\s*$")
NOTES = {"=": "без змін", "~": "оновлено з репозиторію", "✎": "лишаються ваші правки", "⚠": "змінили обидва — потрібне рішення",
         "+": "новий блок у репозиторії", "−": "репозиторій прибрав блок", "✂": "ви прибрали блок",
         "?": "бази немає — невідомо, хто змінив"}
REMOVED_NOTES = {"⚠": "репозиторій прибрав блок, а у вас правки — theirs прибере, mine лишить текст як ваш",
                 "?": "репозиторій не має цього блоку, а бази немає — theirs прибере, mine лишить текст як ваш"}
REMOVED_LINE = "(репозиторій прибрав цей блок)"
BEHIND_NOTE = "джерело позаду вашої бази"         # a "=" whose source offers an older base of yours (`behind`)
REJECTED_NOTE = "відкинуто вами — не застосовується, доки ядро не змінить блок"   # a text you rejected by undoing a sync pass
RULE_NOTE = " (правило ядра)"                   # after the note of a block the repository holds as a rule (`is_rule`)
QUESTIONS = ("⚠", "+", "?")                     # the signs that need an answer
REWRITES = ("~", "−")                           # the signs an apply without decisions acts on: it rewrites the record that holds the block
OFFERS = ("~", "+", "−", "⚠", "?")              # the signs whose row offers the repository's text (or its removal) — a rejection can apply


clip = cc.clip                          # one line, safe to print, at most `limit` characters (since v3.14 in ctx_common)


def base_version(state):
    """The version most blocks of a repository have a base at: the `v` of the state's entries that hold a base
    (a `v` that is not text, in a hand-edited state, is ignored), the first block by id on a tie; None when no block has a base or none of them knows its version. The state's own
    `version` is not consulted (adopt leaves it unset)."""
    blocks = (state or {}).get("blocks") or {}
    count = collections.Counter(blocks[b]["v"] for b in sorted(blocks)
                                if (blocks[b].get("base_sha") or blocks[b].get("bases")) and isinstance(blocks[b].get("v"), str)
                                and blocks[b]["v"])
    return count.most_common(1)[0][0] if count else None


def based_count(state):
    """How many blocks of a repository the store holds a base for: the entries of the state with a `base_sha` or
    `bases`, those you removed (`user_removed`) not counted."""
    blocks = (state or {}).get("blocks") or {}
    return sum(1 for e in blocks.values() if (e.get("base_sha") or e.get("bases")) and not e.get("user_removed"))


def _body_lines(text):
    """The normalised lines of a region, without its two marker lines: the version is in the marker, and what the plan
    shows are the words."""
    return [line for line in norm(text).split("\n") if not MARKER_LINE.match(line)]


def _changed(base, side):
    """(the lines of `side` that are new or changed against `base`, the indexes of the `base` lines that were removed
    or changed). difflib's heuristic for popular lines is on (since v3.14.0): it only starts at 200 lines, so a block
    of ordinary length compares as before, and a long one stays quick — the blank lines between paragraphs would
    otherwise make 2000 lines take seconds."""
    added, gone = [], set()
    for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(None, base, side, autojunk=True).get_opcodes():
        if tag in ("replace", "insert"):
            added.extend(side[j1:j2])
        if tag in ("replace", "delete"):
            gone.update(range(i1, i2))
    return added, gone


def _version_only(ref, side):
    """["(лише версія v<a> → v<b>)"] when the words of `side` are those of `ref` and only the `v=` of the begin
    marker moved (a release bumps it on every block); [] when the versions are the same too."""
    a, b = _marker_version(ref), _marker_version(side)
    if a == b:
        return []
    return ["(лише версія v%s → v%s)" % (clip(a or "—", HEADER_CLIP), clip(b or "—", HEADER_CLIP))]


DIFF_MAX = 2000                                 # the lines of each side a comparison reads (since v3.14.0) …
DIFF_CUT = "(порівняно перші %d рядків)" % DIFF_MAX   # … and what it says when a side had more


def _differences(mine, theirs, base):
    """{"theirs", "mine", "base"}: the first DIFF_LINES lines (blank ones skipped, each clipped to LINE_CLIP) of what
    the repository changed, what you changed and what both started from, all against the base text. Without the base
    text ("base" is None) each side is set against the other. A side whose lines are exactly those it is set against
    and whose version moved says only that: "(лише версія v<a> → v<b>)" — a side that removed lines says nothing new.
    `theirs` None is a block the repository removed: its side says so, and what both said is the base's first lines.
    Each side is compared on its first DIFF_MAX lines (since v3.14.0: thousands of lines must not hold a plan or the
    daily sync); when any side had more, "note" is DIFF_CUT and no side says "only the version" on the strength of a
    part of it."""
    m = _body_lines(mine)
    t = None if theirs is None else _body_lines(theirs)
    b = None if base is None else _body_lines(base)
    cut = any(side is not None and len(side) > DIFF_MAX for side in (m, t, b))
    m, t, b = (None if side is None else side[:DIFF_MAX] for side in (m, t, b))
    if b is None:
        said_t = [] if t is None else _changed(m, t)[0]
        said_m, was = (m if t is None else _changed(t, m)[0]), None
        ref_t, ref_m, vref_t, vref_m = m, t, mine, theirs
    else:
        said_t, gone_t = _changed(b, t) if t is not None else ([], set(range(len(b))))
        said_m, gone_m = _changed(b, m)
        was = [b[i] for i in sorted(gone_t | gone_m)]
        ref_t, ref_m, vref_t, vref_m = b, b, base, base

    def first(lines):
        return [c for c in (clip(l, LINE_CLIP) for l in lines if l.strip()) if c][:DIFF_LINES]
    if theirs is None:
        said = [REMOVED_LINE]
    else:
        said = first(said_t) or (_version_only(vref_t, theirs) if t == ref_t and not cut else [])
    out = {"theirs": said, "mine": first(said_m) or (_version_only(vref_m, mine) if m == ref_m and not cut else []),
           "base": None if was is None else first(was)}
    if cut:
        out["note"] = DIFF_CUT
    return out


def _source_label(repo, source):
    """"MCP (<host of the endpoint>)" or "тека" (the core folder)."""
    if source == "mcp":
        try:
            host = urllib.parse.urlsplit(repo["endpoint"]["url"]).hostname
        except ValueError:
            host = None
        return "MCP (%s)" % clip(host, HEADER_CLIP) if host else "MCP"
    return "тека" if source == "folder" else "—"


def namespace_of(repo, fetched):
    """The marker namespace of a repository's regions in your records: the one its fetch read the blocks in (a
    registration with no namespace takes the core manifest's), else the registration's."""
    return fetched.get("namespace") or repo["namespace"]


def _theirs(fetched):
    """({block id: the repository's region text}, {block id: where that text came from}) of a fetch: the blocks of its
    blocks file, and the team region when it was built (a team region built from the core wins over one of the file)."""
    theirs = dict(fetched.get("blocks") or {})
    where = {bid: fetched.get("source") for bid in theirs}
    if fetched.get("team") is not None:
        theirs["team"], where["team"] = fetched["team"], fetched.get("team_source") or fetched.get("source")
    return theirs, where


def offered(theirs):
    """What the repository offers for a block, as the journal's `taken` and the state's `rejected` name it: the hash of
    its normalised text (cs.sha_text(norm(text))), or "removed" when it has none."""
    return REMOVED if theirs is None else cs.sha_text(norm(theirs))


def _held(entry, mine):
    """What `classify` gets for a block: the state's entry when it holds a base — or a removal mark and no region of
    yours — else None (no base: the region you hold now is not one, and a mark with nothing to put back is a removal)."""
    if entry and (entry.get("base_sha") or entry.get("bases")):
        return entry
    return entry if entry and mine is None and entry.get("user_removed") else None


class SourceLost(ValueError):
    """The repository's blocks file holds none of the blocks you have a base for. A wrong file (another product's copy
    under the same namespace), a stale or a cut one would otherwise read as "the repository removed all of them" and an
    apply would delete your regions; `plan` and `apply` refuse it and the command line says the repository is
    unavailable (exit 5), with nothing written."""


def _lost(state, mine, fetched, skip):
    """Why `fetched` is no source for this state (see SourceLost), or None. The blocks you have a base for — your skipped
    blocks aside, and the `team` block when the core folder builds it (it proves nothing about the file) — must be
    present in the file at least once; it only matters when you still hold one of them (otherwise nothing would be
    removed). A genuine removal of some blocks leaves the others in the file. The message counts and names only the
    blocks you still hold (one you removed yourself is no part of the problem) and ends with how to retire them
    when the repository really did."""
    built = fetched.get("team") is not None or bool(fetched.get("team_error"))
    in_file = fetched.get("blocks") or {}
    based = sorted(b for b, e in state["blocks"].items() if (e.get("base_sha") or e.get("bases")) and b not in skip
                   and not (b == "team" and built))
    held = [b for b in based if b in mine]
    if not held or any(b in in_file for b in based):
        return None
    return ("the blocks file holds none of the %d block%s you have a base for (%s) — a wrong, stale or cut file, "
            "not removals; if the repository really retired them, remove those regions by hand "
            "(context-provider-protocol.md §12.2)"          # the ids are bounded so that the hint survives a clip to NOTE_CLIP
            % (len(held), "" if len(held) == 1 else "s", clip(", ".join(held), HEADER_CLIP)))


def source_lost(store, copies, repo, fetched, now):
    """`_lost` for a repository as the plan would see it — your records (the live view), the state — without raising:
    the command line asks it before the lock, so a lost source stops `provider apply` with nothing written. None also
    for a fetch that failed (that is reported on its own)."""
    if fetched.get("error"):
        return None
    records, _, _ = cr._live_view(store, copies, now)
    mine = find_regions(records, namespace_of(repo, fetched))[0]
    return _lost(load_state(store, repo["id"]), mine, fetched, set(repo.get("skip_blocks") or ()))


# ------------------------------------------------------------------ the overlay (since v3.23.0)
OVERLAY_NOTE = "оверлей накладається"
OVERLAY_MINE_NOTE = " · оверлей не накладено: твої правки"
OVERLAY_BLOCKED_NOTE = " · оверлей не прочитано — блок утримано"


def overlay_of(store, repo_id):
    """(the operations of `overlays/<repo>.yaml` — [] when there is no file —, the reason it cannot be read or None)."""
    try:
        doc = ov.load(store.root, repo_id)
    except ov.Unreadable as e:
        return [], clip(str(e), NOTE_CLIP)
    return (doc["ops"] if doc else []), None


def _stands_for(store, rid, mine, entry, ops, refs):
    """The base text your region stands for when it is the overlay's form of a base and you did not edit it — the text
    the overlay last wrote (`overlay_sha` of `overlay_of`), or the overlay of the present base as the operations give it
    now — else None (a region with no overlay, or one you changed)."""
    if mine is None or not entry:
        return None
    nm = norm(mine)
    sha = cs.sha_text(nm)
    if entry.get("overlay_sha") == sha and entry.get("overlay_of"):
        base = get_base(store, rid, entry["overlay_of"])
        if base is not None:
            return base
    bops = ov.for_block(ops, block_id(mine))
    if bops and entry.get("base_sha"):
        base = get_base(store, rid, entry["base_sha"])
        if base is not None and norm(base) != nm and norm(ov.overlay(base, bops, refs)[0]) == nm:
            return base
    return None


def _reverted(mine, entry, stands):
    """Did you edit an overlaid region back to a text of the core by hand? The state says the overlay wrote the region
    (`overlay_sha`), the region is no longer that text nor the overlay's form of the base, and it is one of the bases."""
    if mine is None or stands is not None or not entry or not entry.get("overlay_sha"):
        return False
    sha = cs.sha_text(norm(mine))
    return sha != entry["overlay_sha"] and (sha == entry.get("base_sha") or sha in (entry.get("bases") or ()))


def block_id(region_text):
    return ov.block_of(region_text)


def _overlay_row(row, mine, stands, theirs, entry, bops, refs, error):
    """What the overlay means for one row of the plan (in place): `overlay` — the results of this block's operations on
    the text that would be written; `reoverlay` (with `overlay_text` and `overlay_of`) — a "=" row whose region is to
    be rewritten because the overlay's form of its base differs from it (a new or changed operation, a held one, the
    file gone); `overlay_blocked` — a row of a block that carries the overlay while the file cannot be read: held, so
    the core's text never replaces your overlaid one unseen. A region you edited is never overlaid (its note says so)."""
    sign = row["sign"]
    carries = bool(entry and entry.get("overlay_sha"))
    if sign == SKIPPED:
        return
    if error:
        if carries:
            row["overlay_blocked"] = True
            row["note"] = clip(row["note"] + OVERLAY_BLOCKED_NOTE, NOTE_CLIP)
        return
    if sign in ("~", "+"):
        row["overlay"] = ov.overlay(theirs, bops, refs)[1] if bops else []
    elif sign == "=" and mine is not None and row.get("reverted"):
        row["overlay"] = ov.overlay(theirs, bops, refs)[1] if bops and theirs is not None else []
        row["note"] = clip(row["note"] + OVERLAY_MINE_NOTE, NOTE_CLIP)
    elif sign == "=" and mine is not None:
        src = stands if stands is not None else mine
        desired, results = ov.overlay(src, bops, refs) if bops else (src, [])
        row["overlay"] = results
        if norm(desired) != norm(mine):
            row.update(reoverlay=True, overlay_text=desired, overlay_of=cs.sha_text(norm(src)))
            row["note"] = clip(OVERLAY_NOTE, NOTE_CLIP)
    elif bops and sign in ("✎", "⚠", "?"):
        row["overlay"] = ov.overlay(theirs, bops, refs)[1] if theirs is not None else []
        if mine is not None:
            row["note"] = clip(row["note"] + OVERLAY_MINE_NOTE, NOTE_CLIP)


def _overlaid(text, ops, refs, ns=None):
    """The overlay's form of a repository's region text (the text itself when no operation of its block applies, or when
    the result would not be one sound region of the block — a marker an operation brought in)."""
    bid = block_id(text)
    bops = ov.for_block(ops, bid)
    if not bops or text is None:
        return text
    out = ov.overlay(text, bops, refs)[0]
    return out if ns is None or _sound(out, ns, bid) else text


def _mark_overlay(entry, written, source):
    """Remember in the block's entry what the overlay wrote: `overlay_sha` (the hash of the region written) and
    `overlay_of` (the base it was made of) — or forget both when the region is the base itself."""
    if norm(written) != norm(source):
        entry["overlay_sha"], entry["overlay_of"] = cs.sha_text(norm(written)), cs.sha_text(norm(source))
    else:
        entry.pop("overlay_sha", None)
        entry.pop("overlay_of", None)


# ------------------------------------------------------------------ the core's changes into your sections (v3.23.0)
SUGGEST_SOURCE = "ctx-provider"                 # the inbox's source of these proposals: ctx's own, not a skill
SUGGEST_MIN_LINE, SUGGEST_MIN_VALUE = 12, 3


def _fields(lines):
    """{label without regard to case: (label, value)} of the field lines `- **Label:** value` (the first of a label)."""
    out = {}
    for ln in lines:
        m = ov.FIELD.match(ln.rstrip("\r"))
        if m:
            out.setdefault(" ".join(m.group(2).split()).casefold(), (m.group(2), m.group(3).strip()))
    return out


def _unbullet(line):
    """A line without its list marker (`- `, `* `, `1. `): the core's prose line and yours as a bullet are the same."""
    return re.sub(r"^(?:[-*+]|\d+[.)])\s+", "", line.strip())


def core_suggestions(old, new, records, ops, rid, from_v, to_v, today):
    """The REPLACE deltas (context-delta/1, source `repo:<rid>`) that bring your own text in step with what the core
    changed in a block between `old` (the base you had) and `new` (its text now) — both whole regions. A field the core
    changed (`- **Label:** a` → `- **Label:** b`) is proposed for every line of yours with that label and value `a`; a
    whole line the core changed (12+ characters, no field, no heading) for every line of yours that reads it. Your text
    is each record's body outside every managed region (`records`: dicts with id and body); a line an operation of your
    overlay (`ops`) finds in `old` is never proposed, nor a value under 3 characters. Pure."""
    if old is None or new is None:
        return []
    bid = block_id(new)
    a, b = ov._inner(old)[1], ov._inner(new)[1]
    touched = set()
    for o in ov.for_block(ops, bid):
        for x0, x1 in ov.locate(a, o["target"].get("path", "")):
            touched.update(ln.strip() for ln in a[x0:x1])
    fa, fb = _fields(a), _fields(b)
    fields = {k: (fa[k][1], fb[k][1]) for k in fa if k in fb and fa[k][1] != fb[k][1] and len(fa[k][1]) >= SUGGEST_MIN_VALUE
              and not any(ov.FIELD.match(t) and " ".join(ov.FIELD.match(t).group(2).split()).casefold() == k for t in touched)}
    lines = []
    for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(None, a, b, autojunk=False).get_opcodes():
        if tag != "replace" or i2 - i1 != j2 - j1:
            continue
        for x, y in zip(a[i1:i2], b[j1:j2]):
            xs, ys = x.strip(), y.strip()
            if (len(xs) >= SUGGEST_MIN_LINE and xs not in touched and not ov.FIELD.match(x) and not ov.HEADING.match(xs)
                    and "<!--" not in xs and ys):
                lines.append((_unbullet(xs), _unbullet(ys)))
    if not fields and not lines:
        return []
    out, seen = [], set()
    ref = "блок %s v%s→v%s" % (bid, from_v or "?", to_v or "?")
    for rec in records:
        own = cc.strip_managed_regions(rec.get("body") or "").replace("\r\n", "\n").split("\n")
        for ln in own:
            st = ln.strip()
            m = ov.FIELD.match(ln)
            hit = None
            if m:
                k = " ".join(m.group(2).split()).casefold()
                if k in fields and m.group(3).strip() == fields[k][0]:
                    hit = (st, "%s %s" % (m.group(1).strip(), fields[k][1]), "%s: %s → %s" % (m.group(2), fields[k][0], fields[k][1]))
            if hit is None and st:
                bullet = st[:len(st) - len(_unbullet(st))]
                pair = next((y for x, y in lines if x == _unbullet(st)), None)
                if pair is not None:
                    hit = (st, bullet + pair, "%s → %s" % (clip(st, HEADER_CLIP), clip(bullet + pair, HEADER_CLIP)))
            if hit is None or (rec["id"], hit[0]) in seen:
                continue
            seen.add((rec["id"], hit[0]))
            out.append({"op": "REPLACE", "record": rec["id"], "text": hit[0], "value": hit[1],
                        "reason": clip("ядро %s v%s→v%s змінило: %s (блок %s)" % (rid, from_v or "?", to_v or "?", hit[2], bid), NOTE_CLIP),
                        "source": {"kind": "repo:%s" % rid, "ref": ref, "at": today}})
    return out


def _overlay_journal(p):
    """({block: [applied ids]}, {block: [held ids]}) of a plan — for the journal line, empty when there is no overlay."""
    done, held = {}, {}
    for bid, results in (p.get("overlay") or {}).items():
        a = [r["id"] for r in results if r["state"] == "applied"]
        h = [r["id"] for r in results if r["state"] != "applied"]
        if a:
            done[bid] = a
        if h:
            held[bid] = h
    return done, held


def _suggest(store, rid, old, taken, theirs, ops, now, to_v):
    """The core's changes into your sections (`core_suggestions`) for every block whose new text went into your records
    and that had a base, as inbox deltas from `ctx-provider` — after the snapshot, so `ctx undo` of the pass takes them
    back. An inbox that cannot be read gets nothing (the pass is not stopped). Returns the sigs of the new entries."""
    import ctx_inbox as ci_                             # here: ctx_inbox reads records, it never needs the blocks
    records, deltas = None, []
    for bid, sha in taken.items():
        entry = old["blocks"].get(bid) or {}
        if sha == REMOVED or not entry.get("base_sha") or theirs.get(bid) is None:
            continue
        base = get_base(store, rid, entry["base_sha"])
        if base is None or norm(base) == norm(theirs[bid]):
            continue
        records = store.load() if records is None else records
        deltas += core_suggestions(base, theirs[bid], records, ops, rid, entry.get("v"), _marker_version(theirs[bid]), now[:10])
    if not deltas:
        return []
    try:
        box = ci_.load(store)
    except cs.StoreError:
        return []
    results = ci_.propose(box, deltas, SUGGEST_SOURCE, records, now[:10])
    new = {r["n"] for r in results if r["status"] == ci_.ADDED}
    if not new:
        return []
    ci_.save(store, box, now[:10])
    return [e["sig"] for e in box["entries"] if e["n"] in new]


def overlay_lines(p):
    """The plan's lines about the overlay (since v3.23.0): the file that cannot be read, and each operation that is held
    or refused — the question `ctx overlay show` and `/context overlay` ask."""
    out = []
    if p.get("overlay_error"):
        out.append("оверлей не прочитано: %s — блоки з оверлеєм утримано" % clip(p["overlay_error"], NOTE_CLIP))
    for bid, results in (p.get("overlay") or {}).items():
        for r in results:
            if r["state"] != "applied":
                out.append("оверлей чекає рішення: %s (%s) — %s — ctx overlay show" % (
                    clip(r["id"], HEADER_CLIP), clip(bid, HEADER_CLIP), clip(r["why"], NOTE_CLIP)))
    return out


def plan(store, copies, repo, fetched, now, all_=False):
    """The plan of one repository: what each of its blocks is in your context against what the repository publishes
    now (`fetched`, from `ctx_repos.fetch` with no `error`; with `all_` it should have been fetched with
    `include_skipped`). Reads only — no lock, nothing written.

    Returns {"repo", "source" ("mcp" | "folder"), "source_label", "version" (the repository's), "base_version" ("—" when no
    block has a base), "rows": [{"block", "sign", "host", "source", "note", "diff"?, "behind"?, "rejected"?, "rule"?}],
    "questions", "changes", "errors", "lagging"}.

    The rows are the blocks in your records (the pending edits of local-context.md count: the live view) followed by
    those only the repository offers; a block absent on both sides is none. `host` is the record that holds your
    region (for "✂", the one that held it); `source` where the repository's text came from (None when it has none).
    A "⚠" row also carries `diff`, the lines each side changed against the base (see `_differences`). The signs are
    `classify`'s, and "·" for a block of `skip_blocks` (listed only with `all_`; yours never appears without it) and
    for the team block when it could not be built (its reason is the note) — neither is a question or a change.
    `questions` counts the rows "⚠", "+" and "?"; `changes` the records an apply without decisions would rewrite: the
    distinct hosts of the rows "~" and "−" — a `rejected` row counts in neither, since apply holds it. `errors` are
    `find_regions`' problems (a block with one has no row).
    A "=" row whose source lags behind your base (`behind`) carries `behind: True` and the note
    "джерело позаду вашої бази (v<theirs> < v<yours>)". `lagging` (since v3.14.0) says the whole copy lags behind your
    bases, on positive evidence (`source_lags`: a block it carries is at an older `v=` than your base of it, none at a
    newer one); then a block you hold a base for that the copy lacks is "=" with the note "джерело позаду вашої бази"
    ("✎" when you edited it), never "−" or "⚠". The daily sync holds every row that would change something on such a
    plan (ctx_synced.decide); a manual apply acts row by row.
    A row that offers the repository's text or its removal ("~", "+", "−", "⚠", "?") whose offer (`offered`: the hash
    of the text, or "removed") is among the state's `rejected` for the block carries `rejected: True` and the note
    "відкинуто вами — не застосовується, доки ядро не змінить блок"; the sign stays `classify`'s. A row whose
    repository text is a core rule (`is_rule`) carries `rule: True`, and " (правило ядра)" ends its note. A blocks file
    that holds none of the blocks you have a base for is no plan at all: SourceLost (see `_lost`).
    Every text a server controls is cleaned of control characters and bounded (HEADER_CLIP, NOTE_CLIP, LINE_CLIP).
    """
    if fetched.get("error"):
        raise ValueError("plan needs a repository that was fetched, not one that failed: %s" % fetched["error"])
    rid, skip = repo["id"], set(repo.get("skip_blocks") or ())
    records, _, _ = cr._live_view(store, copies, now)
    mine, problems = find_regions(records, namespace_of(repo, fetched))
    theirs, where = _theirs(fetched)
    team_error = fetched.get("team_error")
    state = load_state(store, rid)
    lost = _lost(state, mine, fetched, skip)
    if lost:
        raise SourceLost(lost)
    ops, ov_error = overlay_of(store, rid)
    refs = ov.refs_in(records)
    bad = {x["block"] for x in problems if x["block"]}
    ids = [b for b in list(mine) + [b for b in theirs if b not in mine] if b not in bad]
    if team_error and "team" not in ids and "team" not in bad:
        ids.append("team")
    rows, version = [], fetched.get("version")
    lagging = source_lags(state, fetched, skip)          # positive evidence in the blocks the copy carries
    for bid in ids:
        m, t, entry = mine.get(bid), theirs.get(bid), state["blocks"].get(bid)
        row = {"block": bid, "sign": SKIPPED, "host": m["host"] if m else None, "source": where.get(bid), "note": ""}
        if bid in skip:
            if not all_:
                continue
            row["note"] = "пропущено"
        elif bid == "team" and team_error:
            row["note"] = clip("недоступний: " + team_error, NOTE_CLIP)
        else:
            if m is None and t is None:
                continue
            mt = m["text"] if m else None
            stands = _stands_for(store, rid, mt, entry, ops, refs)
            mc = stands if stands is not None else mt     # an overlaid region you did not edit is the base it was made of
            held = _held(entry, mc)
            if _reverted(mt, entry, stands):              # you took the overlay out by hand: your edit, never undone unseen
                gone = cs.sha_text(norm(mt))
                held = dict(held, base_sha=None if held.get("base_sha") == gone else held.get("base_sha"),
                            bases=[h for h in held.get("bases") or () if h != gone])
                row["reverted"] = True
            row["sign"] = classify(mc, t, held, lagging)
            lags = row["sign"] in ("=", "✎") and behind(mc, t, held, lagging)
            row["note"] = REMOVED_NOTES[row["sign"]] if t is None and row["sign"] in REMOVED_NOTES else NOTES[row["sign"]]
            if lags:                                     # the copy lags: its text is an older base, or it lacks the block
                vm, vt = (_marker_version(m["text"]), _marker_version(t)) if t is not None else ("", "")
                row["behind"] = True
                row["note"] = clip(BEHIND_NOTE + (" (v%s < v%s)" % (clip(vt, HEADER_CLIP), clip(vm, HEADER_CLIP))
                                                  if vm and vt and vm != vt else ""), NOTE_CLIP)
            elif row["sign"] == "✂":
                row["host"] = (entry or {}).get("host")
            elif row["sign"] == "~":
                vm, vt = _marker_version(m["text"]), _marker_version(t)
                if vm and vt and vm != vt:
                    row["note"] = clip("%s (v%s → v%s)" % (row["note"], clip(vm, HEADER_CLIP), clip(vt, HEADER_CLIP)), NOTE_CLIP)
            elif row["sign"] == "⚠":
                try:
                    base = get_base(store, rid, entry.get("base_sha")) if entry else None
                except cs.StoreError:
                    base = None
                row["diff"] = _differences(m["text"], t, base)
            if row["sign"] in OFFERS and offered(t) in (state.get("rejected") or {}).get(bid, ()):
                row["rejected"], row["note"] = True, REJECTED_NOTE
            if is_rule(t):
                row["rule"] = True
                row["note"] = clip(row["note"] + RULE_NOTE, NOTE_CLIP)
            _overlay_row(row, mt, stands, t, entry, ov.for_block(ops, bid), refs, ov_error)
        rows.append(row)
    open_rows = [r for r in rows if not r.get("rejected")]   # a rejected text is held by apply: neither asked nor written
    return {"repo": rid, "source": fetched.get("source"), "source_label": _source_label(repo, fetched.get("source")),
            "version": clip(version, HEADER_CLIP) if version else None,
            "base_version": clip(base_version(state) or "—", HEADER_CLIP), "rows": rows,
            "questions": sum(1 for r in open_rows if r["sign"] in QUESTIONS),
            "changes": len({r["host"] for r in open_rows if (r["sign"] in REWRITES or r.get("reoverlay")) and r["host"]
                            and not r.get("overlay_blocked")}),
            "errors": [dict(x) for x in problems if all_ or x["block"] not in skip], "lagging": lagging,
            "overlay": {r["block"]: r["overlay"] for r in rows if r.get("overlay")}, "overlay_error": ov_error,
            "overlay_ops": ops}


def unknown_blocks(p, choose, add):
    """The blocks `choose` ({block: answer}) and `add` name that plan `p` does not have — neither a row (a rejected one
    is a row: theirs or --add takes it) nor a block with a structure error — sorted. `apply` refuses them before it
    writes; `ctx provider apply` asks it before the lock (since v3.14), of a plan made on the same fetch, so that a
    wrong block imports nothing."""
    known = {r["block"] for r in p["rows"]} | {x["block"] for x in p["errors"] if x["block"]}
    return sorted(b for b in set(choose or {}) | set(add or ()) if b not in known)


def no_block(blocks, rid):
    """The message for blocks `unknown_blocks` found."""
    return "no block %s in the plan of %s — `ctx provider plan %s` lists them" % (", ".join(blocks), rid, rid)


def held_rejected(p, choose, add):
    """The blocks a manual `ctx provider apply` holds, in plan order: the rows of plan `p` that offer a text you rejected
    by undoing a sync pass (`rejected: True`; spec v3.14 §5.4, "do not repeat") — unless this pass takes it: `choose`
    says theirs for it (any sign that offers), `add` names a "+", or `choose` answers a "⚠" or a "?" at all. Mine or
    both on a rejected "~", "−" or "+" takes nothing, so the block stays held."""
    out = []
    for r in p["rows"]:
        bid, how = r["block"], (choose or {}).get(r["block"])
        if not r.get("rejected") or r["sign"] not in OFFERS:
            continue
        if how == "theirs" or (r["sign"] == "+" and bid in (add or ())) or (r["sign"] in ("⚠", "?") and how):
            continue
        out.append(bid)
    return out


def _detail_lines(diff):
    """The three lines under a "⚠" row: what the repository says now, what you wrote, what both said before (this
    one only when the base text is there). A side with several changed lines continues on aligned lines. A comparison
    cut at DIFF_MAX lines adds its note on a line of its own."""
    out = []
    for label, key in (("Ядро тепер каже", "theirs"), ("Ви писали", "mine"), ("Раніше обидва казали", "base")):
        lines = diff.get(key)
        if lines is None:
            continue
        head = "    %s: " % label
        out.append(head + (lines[0] if lines else "—"))
        out.extend(" " * len(head) + line for line in lines[1:])
    if diff.get("note"):
        out.append("    " + diff["note"])
    return out


def render_plan(p):
    """The text of a plan: the header, one line per block (a "⚠" with its three versions under it), the errors, and
    the last line `Питань: N · зміниться записів: M`."""
    lines = ["%s · джерело: %s · ядро v%s · база v%s" % (clip(p["repo"], HEADER_CLIP), p["source_label"], p["version"] or "—",
                                                        p["base_version"])]
    rows = p["rows"]
    w_block = max([len(clip(r["block"], HEADER_CLIP)) for r in rows] or [0])
    w_host = max([len(clip(r["host"] or "—", HEADER_CLIP)) for r in rows] or [0])
    for r in rows:
        lines.append(("%s  %s  %s  %s" % (r["sign"], clip(r["block"], HEADER_CLIP).ljust(w_block),
                                           clip(r["host"] or "—", HEADER_CLIP).ljust(w_host), clip(r["note"], NOTE_CLIP))).rstrip())
        if r.get("diff"):
            lines.extend(_detail_lines(r["diff"]))
    if not rows:
        lines.append("блоків цього репозиторію немає")
    for x in p["errors"]:
        lines.append("помилка: %s — %s" % (clip(x["block"] or "?", HEADER_CLIP), clip(x["why"], HEADER_CLIP)))
    lines.extend(overlay_lines(p))
    lines.append("Питань: %d · зміниться записів: %d" % (p["questions"], p["changes"]))
    return "\n".join(lines)


# ------------------------------------------------------------------ apply
CHOICES = ("theirs", "mine", "both")            # the answers to a "⚠" or a "?"
BOTH_THEIRS, BOTH_MINE = "<!-- ctx:both theirs -->", "<!-- ctx:both mine -->"
BLOCK_SERVICE = ("checked", "host")             # what a check moves by itself in a block's entry: no snapshot, no journal line
DETACH = object()                               # an edit that drops a region's markers and keeps its text in place


def _spans(body, ns):
    """{block id: (start, end)} of the sound regions of `ns` in one record's body."""
    return {bid: (start, end) for bid, start, end, _ in _scan(body, ns)[0]}


def _sound(text, ns, bid):
    """Is `text` one whole, well-formed region of `ns` named `bid`, with no other marker of `ns` inside it? Only
    then does a repository's text go into your records: a region nested in it would break your context."""
    regions, errors = _scan(text or "", ns)
    return not errors and len(regions) == 1 and regions[0][:3] == (bid, 0, len(text))


def _cut(body, start, end):
    """`body` without body[start:end] and the line break that ends it; a blank line doubled by the cut is closed up."""
    for nl in ("\r\n", "\n"):
        if body.startswith(nl, end):
            end += len(nl)
            break
    if body[:start].endswith("\n\n") and body.startswith("\n", end):
        end += 1
    return body[:start] + body[end:]


def _inner(text):
    """(begin marker, the text between the markers, end marker) of a region text."""
    head, tail = text.index("-->") + 3, text.rindex("<!--")
    inner = text[head:tail]
    inner = inner[1:] if inner.startswith("\n") else inner
    return text[:head], inner[:-1] if inner.endswith("\n") else inner, text[tail:]


def _detach(region):
    """A region's own text without its two markers — what stays in your record when you keep a block the repository
    removed ("" when there is none)."""
    return _inner(region)[1]


def _both(theirs, mine):
    """ONE region with the repository's markers (its v= too): the repository's text, then yours, each under its mark."""
    begin, said, end = _inner(theirs)
    return "\n".join([begin, BOTH_THEIRS, said, BOTH_MINE, _inner(mine)[1], end])


def _at_end(body, ns, texts):
    """`body` with the regions `texts` added at its end, a blank line before each — before the end of the
    `<ns>:section` wrapper when the record holds one."""
    add = "\n\n".join(texts)
    ends = list(re.finditer(r"<!--\s*%s:section:end\s*-->" % re.escape(ns), body))
    if ends:
        pos = ends[-1].start()
        return body[:pos].rstrip("\n") + "\n\n" + add + "\n" + body[pos:]
    head = body.rstrip("\n")
    return head + "\n\n" + add + body[len(head):]


def _home_record(repo, mine, records, title):
    """Where a new block of the repository goes: the registration's `home_record` when it names one of your records;
    else the record that holds most of the repository's regions (the first in order on a tie); else your custom
    record titled as the repository; else None — a new record is made."""
    ids = [r["id"] for r in records]
    if repo.get("home_record") in ids:
        return repo["home_record"]
    count = collections.Counter(found["host"] for found in mine.values())
    if count:
        top = max(count.values())
        return next(i for i in ids if count.get(i) == top)
    return next((r["id"] for r in records if r["type"] == "custom" and r["title"] == title), None)


def _rebase(entry, text):
    """The repository's `text` becomes the block's base: its hash the newest of the history, its version the entry's."""
    sha = cs.sha_text(norm(text))
    if entry.get("base_sha") != sha:
        entry["bases"] = [h for h in (entry.get("bases") or []) if h != sha] + [sha]
        entry["base_sha"] = sha
    entry["v"] = _marker_version(text)


def _substance(state):
    """What of a state counts as a change: every block entry, without the time it was checked and its host."""
    return {bid: {k: v for k, v in b.items() if k not in BLOCK_SERVICE} for bid, b in _clean(state, "state")["blocks"].items()}


def apply(store, copies, home, repo, fetched, choose, add, now, op="provider-apply", hold=()):
    """One pass of `repo` over your context, from `fetched` (`ctx_repos.fetch` with no `error`). The caller holds the
    lock and has imported the edits of local-context.md first: with edits still waiting it is refused (co.Refused),
    and nothing is written.

    The signs are `plan`'s — the plan is made here, on the records as they are now (a lost source, SourceLost, stops
    it before anything is written) — and each is acted on (spec B6):
      =   nothing in the records; the base becomes the repository's text when it was not — except when the source lags
          behind your base (`behind`): then the base stays as it is
      ~   the region becomes the repository's text, and so does the base
      ✎   your region stays, the base too — unless `choose` says theirs for it (since v3.14.0): then the region becomes
          the repository's text and so does the base (mine or both for a "✎" is no answer: `ignored`; nor is theirs
          for a "✎" whose lagging source lacks the block)
      −   the region is removed (its text stays in the snapshot), and the block's state entry with it
      ✂   nothing in the records; the state marks it removed by you (`user_removed`, today) — never offered again
      ⚠ ? only with an answer in `choose` {block: "theirs" | "mine" | "both"}: theirs — the region becomes the
          repository's; mine — yours stays; both — ONE region with the repository's markers holding its text under
          `<!-- ctx:both theirs -->` and yours under `<!-- ctx:both mine -->`. The base becomes the repository's text
          in all three, so the next plan sees yours as your edit ("✎") and does not ask again.
          A block the repository removed (yours edited, or no base): theirs — the region is removed; mine — its
          markers are removed and its text stays in place as your own; the state entry goes in both, so it is never
          asked again; both is no answer (ValueError)
      +   only when the block is in `add`: the repository's region goes at the end of the home record (see
          `_home_record`; inside its `<ns>:section` wrapper when it has one), or into a new custom record
          `## <the registration's title>` at the end of your context
      ·   and the blocks with structure errors (`find_regions`) are never touched
    A "⚠", "?" or "+" without its answer waits (`pending`); everything else is applied. A repository region that is
    not one sound region of its block is never written into a record: that block goes to `errors`, untouched.

    `hold` (since v3.14.0) names blocks this pass does not touch, whatever their sign and whatever `choose` / `add`
    say of them: each is listed in `held` with its sign — not in `pending`, `ignored`, `applied` or the journal's
    decisions — and nothing of it changes but the time its entry was checked. The daily sync holds what its cascade
    leaves alone; `ctx provider apply` holds the rows that offer a text you rejected (`held_rejected`). Theirs for such a
    row — any sign that offers, "~", "−" and "+" too — is the explicit take: the text (or the removal) is applied as
    the sign says and the base moves, so the next plan has no mark; for a "+" it is its --add.

    The order: snapshot `op` → the new base texts → the host records (verified today, source "repo:<id>") → the
    state (checked, source, version; per block v, host, checked) → the base texts nobody refers to are pruned → one
    journal line {op: `op`, source repo:<id>, from_v, to_v, ids: the records written, decisions: {block: sign, or
    "<sign> <answer>"}, pending, taken, snapshot} → the compiled copies. `op` is "provider-apply" unless the caller
    labels the pass ("provider-sync"). `taken` is {block: offered(text)} for every block whose repository text went
    into your records ("~", "+", theirs, both — the repository's text, not the joined one) and {block: "removed"} for
    every block removed ("−", theirs for a block the repository removed); a block kept as yours (mine, ✎) is not in
    it. A pass that changes nothing but the time of the check writes the state file alone: no snapshot, no journal
    line, no record.

    A `choose` value that is not an answer, or a block in `choose` / `add` / `hold` that the plan does not have →
    ValueError before anything is written; an answer for a block that needs none is left out and listed in `ignored`
    with its sign — and one for a block the plan refuses (broken markers: it is in `errors`, not in the rows) with "!".

    Returns {"repo", "plan", "applied": {block: sign}, "decisions", "pending": [block], "ignored": {block: sign},
    "held": {block: sign}, "errors", "changed": bool, "written": [record ids], "snapshot": folder or None,
    "compiled": [copies]}.
    """
    if fetched.get("error"):
        raise ValueError("apply needs a repository that was fetched, not one that failed: %s" % fetched["error"])
    choose, add, hold = dict(choose or {}), list(add or []), set(hold or ())
    wrong = ["%s=%s" % (b, how) for b, how in choose.items() if how not in CHOICES]
    if wrong:
        raise ValueError("--choose takes BLOCK=theirs|mine|both, not %s" % ", ".join(wrong))
    waiting = co.plan_sync(store, copies)
    if sum(co.pending(waiting).values()) + len(waiting["conflicts"]) + len(waiting["missing"]):
        raise co.Refused("changes to local-context.md or to the records wait to be imported — `ctx sync` first, then apply")
    rid, ns = repo["id"], namespace_of(repo, fetched)
    p = plan(store, copies, repo, fetched, now)
    unknown = unknown_blocks(p, choose, set(add) | hold)
    if unknown:
        raise ValueError(no_block(unknown, rid))
    hold |= {r["block"] for r in p["rows"] if r.get("overlay_blocked")}   # an unreadable overlay: never unseen
    records = store.load()
    ops = [] if p.get("overlay_error") else p.get("overlay_ops") or []      # the file as the plan read it
    refs = ov.refs_in(records)
    by_id = {r["id"]: r for r in records}
    mine = find_regions(records, ns)[0]
    theirs = _theirs(fetched)[0]
    old = load_state(store, rid)
    state = copy.deepcopy(old)
    checked, today = fetched.get("checked") or now, now[:10]
    edits, rebased, adds, taken = {}, {}, [], {}
    overlaid = {}                                       # block: (the text written, the repository text it was made of)
    applied, decisions, pending, ignored, refused, held = {}, {}, [], {}, [], {}
    broken = {x["block"] for x in p["errors"] if x["block"]} - {r["block"] for r in p["rows"]}
    for bid in sorted(((set(choose) | set(add)) & broken) - hold):
        ignored[bid] = "!"                              # an answer for a block with broken markers: not applied, and said so
    for row in p["rows"]:
        bid, sign = row["block"], row["sign"]
        m, t, entry = mine.get(bid), theirs.get(bid), state["blocks"].get(bid)
        if bid in hold:                                 # not this pass's: only the time of the check moves
            held[bid] = sign
            if entry and sign != SKIPPED:
                entry["checked"] = checked
            continue
        how, wanted = choose.get(bid), bid in add
        # theirs on a ✎, or on a row that offers a text you rejected (the explicit take), is an answer too — but not on a
        # ✎ whose source lags and lacks the block: there is no text of the repository to take
        answers = sign in ("⚠", "?") or (how == "theirs" and ((sign == "✎" and t is not None)
                                                              or bool(row.get("rejected"))))
        if (how and not answers) or (wanted and sign != "+"):
            ignored[bid] = sign                         # an answer to a question the plan does not ask: dropped
        wanted = (wanted or (answers and sign == "+")) and sign == "+"    # theirs on a rejected "+" is its --add
        how = how if answers and sign != "+" else None
        if sign == SKIPPED:
            continue
        if (sign in ("⚠", "?") and not how) or (sign == "+" and not wanted):
            pending.append(bid)
            if entry:
                entry["checked"] = checked
            continue
        gone = t is None and sign in ("⚠", "?")        # the repository removed a block you edited (or never had a base for)
        if gone and how == "both":
            raise ValueError("both is not possible for a block the repository removed: %s — theirs removes it, mine keeps "
                             "your text without its markers" % bid)
        takes = sign in ("~", "+") or (how in ("theirs", "both") and t is not None)   # the repository's text goes into a record
        if takes and not _sound(t, ns, bid):
            refused.append({"block": bid, "host": row["host"], "why": "the repository's region is not well-formed"})
            continue
        if takes:
            taken[bid] = offered(t)
        elif sign == "−" or (gone and how == "theirs"):
            taken[bid] = REMOVED
        if sign == "−" or gone:
            edits.setdefault(m["host"], {})[bid] = DETACH if gone and how == "mine" else None
            state["blocks"].pop(bid, None)
        elif sign == "✂":
            entry["user_removed"] = entry.get("user_removed") or today
            entry["checked"] = checked
        else:
            if sign == "~" or how == "theirs":
                w = _overlaid(t, ops, refs, ns)
                edits.setdefault(m["host"], {})[bid] = w
                overlaid[bid] = (w, t)
            elif how == "both":
                edits.setdefault(m["host"], {})[bid] = _both(t, m["text"])
            elif sign == "+":
                adds.append(bid)
                overlaid[bid] = (_overlaid(t, ops, refs, ns), t)
            elif row.get("reoverlay"):
                edits.setdefault(m["host"], {})[bid] = row["overlay_text"]
                overlaid[bid] = (row["overlay_text"], None)
            entry = state["blocks"].setdefault(bid, {"base_sha": None, "bases": [], "v": "", "host": None, "checked": None,
                                                     "user_removed": None})
            if (sign != "✎" or how == "theirs") and not row.get("behind"):   # a source behind your base never moves the base back
                _rebase(entry, t)
                rebased[bid] = t
            entry.update(host=m["host"] if m else None, checked=checked, user_removed=None)
            if bid in overlaid:
                w, src = overlaid[bid]
                if src is None:
                    entry["overlay_sha"], entry["overlay_of"] = cs.sha_text(norm(w)), row["overlay_of"]
                    if entry["overlay_sha"] == entry["overlay_of"]:
                        entry.pop("overlay_sha"); entry.pop("overlay_of")
                else:
                    _mark_overlay(entry, w, src)
        applied[bid] = sign
        decisions[bid] = "%s %s" % (sign, how) if how else sign

    bodies = {}
    for host, block_edits in edits.items():
        body = by_id[host]["body"]
        spans = _spans(body, ns)
        for bid in sorted(block_edits, key=lambda b: spans[b][0], reverse=True):   # from the end: earlier offsets stay true
            start, end = spans[bid]
            new = _detach(body[start:end]) if block_edits[bid] is DETACH else block_edits[bid]
            body = _cut(body, start, end) if not new else body[:start] + new + body[end:]
        bodies[host] = body
    title = clip(repo.get("title") or rid, HEADER_CLIP)
    new_record = None
    if adds:
        home_id = _home_record(repo, mine, records, title)
        if home_id:
            bodies[home_id] = _at_end(bodies.get(home_id, by_id[home_id]["body"]), ns, [overlaid[b][0] for b in adds])
            for bid in adds:
                state["blocks"][bid]["host"] = home_id
        else:
            new_record = {"text": "## %s\n\n%s\n" % (title, "\n\n".join(overlaid[b][0] for b in adds)), "type": cs._h2_type(title),
                          "title": title, "after": records[-1]["id"] if records else None}
    state.update(checked=checked, source=fetched.get("source"), version=fetched.get("version"))
    res = {"repo": rid, "plan": p, "applied": applied, "decisions": decisions, "pending": pending, "ignored": ignored,
           "held": held, "errors": [dict(x) for x in p["errors"]] + refused, "written": [], "snapshot": None, "compiled": [],
           "overlay": p.get("overlay") or {}, "overlay_error": p.get("overlay_error"),
           "changed": bool(bodies or new_record) or _substance(old) != _substance(state)}
    if not res["changed"]:
        save_state(store, rid, state)                  # the time of the check, and nothing else
        return res
    snap = co.snapshot(store, copies, home, op)
    for text in rebased.values():
        put_base(store, rid, text)
    source = "repo:" + rid
    for host, body in bodies.items():
        if body != by_id[host]["body"]:
            store.write(co.touch(dict(by_id[host], body=body, source=source, modified=now), now))
            res["written"].append(host)
    if new_record:
        made = co._insert(store, [new_record], source, now)
        for bid in adds:
            state["blocks"][bid]["host"] = made[0]
        res["written"].extend(made)
    save_state(store, rid, state)
    proposed = _suggest(store, rid, old, taken, theirs, ops, now, fetched.get("version"))
    prune_bases(store, rid, state)
    line = {"ts": now, "op": op, "source": source, "from_v": old.get("version") or base_version(old),
            "to_v": fetched.get("version"), "ids": res["written"], "decisions": decisions, "pending": pending,
            "taken": taken, "snapshot": snap}
    kept = {r["block"] for r in p["rows"] if r["sign"] == "=" and not r.get("reverted")} - set(held)
    was = {b: (old["blocks"].get(b) or {}).get("base_sha") for b in taken if (old["blocks"].get(b) or {}).get("base_sha")}
    if was:                                             # since v3.23.0: the base each taken text replaced (ctx history)
        line["was"] = was
    if proposed:
        line["proposed"] = proposed
    res["proposed"] = proposed
    done, waiting = _overlay_journal({"overlay": {b: x for b, x in (p.get("overlay") or {}).items()
                                                  if (b in overlaid or b in kept) and b in applied}})
    if done:
        line["overlay"] = done
    if waiting:
        line["overlay_held"] = waiting
    store.journal(line)
    if res["written"]:
        res["compiled"] = co.compile_store(store, copies, now, home, snap)["written"]
    res["snapshot"] = snap
    return res


# ------------------------------------------------------------------ `ctx overlay` (since v3.23.0)
OVERLAY_OP = "overlay"                          # the journal's op and the snapshot's label of `ctx overlay …`
STATES = {"rewrite": "оверлей накладається", "same": "без змін", "edited": "не накладено: твої правки",
          "clean": "оверлею тут немає — забуваю, що він писав",
          "behind": "не накладено: регіон відстає від бази — спершу ctx provider apply", "no-base": "не накладено: немає бази — ctx provider adopt"}


def _ov_code(rid, ops, rows):
    """The code of an overlay plan: the operations and, per block, what is there and what would be written."""
    h = cs.sha_text(json.dumps([rid, ov.dump({"schema": ov.SCHEMA, "repo": rid, "ops": ops}),
                                [[r["block"], r["state"], cs.sha_text(norm(r.get("before") or "")),
                                  cs.sha_text(norm(r.get("after") or ""))] for r in rows]], ensure_ascii=False))
    return h[:8]


def reoverlay(store, copies, home, repo, now, ops, doc=None, apply=False, action="apply", what=None):
    """Lay the operations `ops` over every block of `repo` you hold a base for — from the base the store keeps, no fetch
    of the repository — and, with `apply`, write it. `doc` is the overlay document to save as `overlays/<repo>.yaml`
    (None: the file stays as it is). The region of a block is rewritten only when it is the base itself or the
    overlay's form of the base under the operations of the file as it is now (you did not edit it); a region you edited
    is "edited", one whose overlay was made of an older base "behind", a block with operations and no base "no-base".

    Returns {"repo", "rows": [{"block", "host", "state": rewrite | same | edited | behind | no-base, "results", "before",
    "after"}], "code", "changed", "written", "snapshot", "compiled"}. The code (`_ov_code`) names the operations and
    every region before and after: `apply` checks it is the one the caller showed (the command line does). With `apply`
    — the lock held and the edits waiting imported by the caller — one snapshot `overlay`, the file, the records,
    the block state (`overlay_sha` / `overlay_of`), one journal line {op: overlay, action, what, ids, overlay,
    overlay_held, snapshot}, the compile. Nothing to write and the file unchanged → nothing written."""
    rid = repo["id"]
    ns = repo.get("namespace") or rid
    records = store.load()
    by_id = {r["id"]: r for r in records}
    mine = find_regions(records, ns)[0]
    state = load_state(store, rid)
    old_ops = overlay_of(store, rid)[0]
    refs = ov.refs_in(records)
    rows = []
    for bid, m in mine.items():
        entry = state["blocks"].get(bid) or {}
        bnew = ov.for_block(ops, bid)
        base = get_base(store, rid, entry.get("base_sha")) if entry.get("base_sha") else None
        if base is None:
            if bnew:
                rows.append({"block": bid, "host": m["host"], "state": "no-base", "results": [], "before": m["text"],
                             "after": m["text"]})
            continue
        mt = m["text"]
        stands = base if norm(mt) == norm(base) and not _reverted(mt, entry, None) \
            else _stands_for(store, rid, mt, entry, old_ops, refs)
        if stands is None and not bnew and entry.get("overlay_sha") and norm(mt) == norm(base):
            rows.append({"block": bid, "host": m["host"], "state": "clean", "results": [], "before": mt, "after": mt})
            continue                                    # your hand revert, and no operation left: nothing to remember
        if stands is None or norm(stands) != norm(base):
            if bnew or entry.get("overlay_sha"):
                rows.append({"block": bid, "host": m["host"], "state": "edited" if stands is None else "behind",
                             "results": ov.overlay(base, bnew, refs)[1] if bnew else [], "before": mt, "after": mt})
            continue
        after, results = ov.overlay(base, bnew, refs) if bnew else (base, [])
        if not bnew and norm(after) == norm(mt):
            if entry.get("overlay_sha"):                # no operation and the core's text: forget what the overlay wrote
                rows.append({"block": bid, "host": m["host"], "state": "clean", "results": [], "before": mt, "after": mt})
            continue
        rows.append({"block": bid, "host": m["host"], "state": "same" if norm(after) == norm(mt) else "rewrite",
                     "results": results, "before": mt, "after": after})
    known = set(mine)
    for o in ops:                                       # an operation for a block you do not hold
        if o["target"]["block"] not in known and not any(r["block"] == o["target"]["block"] for r in rows):
            rows.append({"block": o["target"]["block"], "host": None, "state": "no-block", "results": [], "before": None,
                         "after": None})
            known.add(o["target"]["block"])
    res = {"repo": rid, "rows": rows, "code": _ov_code(rid, ops, rows), "changed": False, "written": [], "snapshot": None,
           "compiled": []}
    if not apply:
        return res
    try:
        current = ov.load(store.root, rid)
    except ov.Unreadable:
        current = None
    doc_changes = doc is not None and (current is None or ov.dump(current) != ov.dump(dict(doc, repo=rid)))
    rewrites = [r for r in rows if r["state"] == "rewrite"]
    if not rewrites and not doc_changes and not any(r["state"] == "clean" for r in rows):
        return res
    snap = co.snapshot(store, copies, home, OVERLAY_OP)
    if doc_changes:
        ov.save(store.root, rid, doc, replace_unreadable=True)
    bodies = {}
    for r in rewrites:
        body = bodies.get(r["host"], by_id[r["host"]]["body"])
        start, end = _spans(body, ns)[r["block"]]
        bodies[r["host"]] = body[:start] + r["after"] + body[end:]
    new_state = copy.deepcopy(state)
    for r in rows:
        if r["state"] in ("rewrite", "same"):
            entry = new_state["blocks"][r["block"]]
            _mark_overlay(entry, r["after"], get_base(store, rid, entry["base_sha"]))
        elif r["state"] == "clean":
            new_state["blocks"][r["block"]].pop("overlay_sha", None)
            new_state["blocks"][r["block"]].pop("overlay_of", None)
    source = "ctx-overlay"
    for host, body in bodies.items():
        store.write(co.touch(dict(by_id[host], body=body, source=source, modified=now), now))
        res["written"].append(host)
    save_state(store, rid, new_state)
    done, held = _overlay_journal({"overlay": {r["block"]: r["results"] for r in rows
                                               if r["results"] and r["state"] in ("rewrite", "same")}})
    line = {"ts": now, "op": OVERLAY_OP, "action": action, "source": source, "repo": rid, "ids": res["written"],
            "snapshot": snap}
    if what:
        line["what"] = what
    if done:
        line["overlay"] = done
    if held:
        line["overlay_held"] = held
    store.journal(line)
    if res["written"]:
        res["compiled"] = co.compile_store(store, copies, now, home, snap)["written"]
    res.update(changed=True, snapshot=snap)
    return res


def _diff_lines(before, after, limit=12):
    """The lines a rewrite takes away (−) and adds (+), at most `limit`, then «ще N»."""
    out = []
    for ln in difflib.ndiff(norm(before).split("\n"), norm(after).split("\n")):
        if ln[:2] in ("- ", "+ "):
            out.append("    %s %s" % ("−" if ln[0] == "-" else "+", clip(ln[2:], LINE_CLIP)))
    return out[:limit] + (["    … ще %d" % (len(out) - limit)] if len(out) > limit else [])


def render_overlay(res, ops, show_diff=True):
    """The text of an overlay plan or apply: one line per operation (its block › path, what it does, found/expected, its
    state and reason), one line per block with what happens to it and — for a rewrite — the lines it changes, the code."""
    lines = ["%s · оверлей: %d операці%s" % (clip(res["repo"], HEADER_CLIP), len(ops), "я" if len(ops) == 1 else "й")]
    state_of, row_of = {}, {}
    for r in res["rows"]:
        for x in r["results"]:
            state_of[x["id"]] = x
            row_of[x["id"]] = r["state"]
    for o in ops:
        x = state_of.get(o["id"])
        tgt = o["target"]["block"] + ((" › " + o["target"]["path"]) if o["target"].get("path") else "")
        if x is None:
            st = "блоку немає в записах"
        elif row_of.get(o["id"]) in ("edited", "behind", "no-base"):
            st = STATES[row_of[o["id"]]]
        elif x["state"] == "applied":
            st = "діє (знайдено %d)" % x["found"]
        else:
            st = "затримано: %s" % x["why"]
        lines.append("  %s · %s · %s · %s%s" % (clip(o["id"], HEADER_CLIP), clip(tgt, NOTE_CLIP), o["op"], st,
                                                (" · " + clip(o["reason"], NOTE_CLIP)) if o.get("reason") else ""))
    for r in res["rows"]:
        lines.append("%s · %s%s" % (clip(r["block"], HEADER_CLIP), STATES.get(r["state"], "блоку немає в записах"),
                                    (" · " + clip(r["host"], HEADER_CLIP)) if r["host"] else ""))
        if show_diff and r["state"] == "rewrite":
            lines.extend(_diff_lines(r["before"], r["after"]))
    lines.append("код: %s" % res["code"])
    return "\n".join(lines)


def render_apply(res):
    """The text of an apply: the plan's table (a "⚠" with its three versions under it), then what was not needed,
    what was held (`утримано: <sign> <block> — цей прохід його не чіпав`, and for a text you rejected
    ` · взяти текст ядра: --choose <block>=theirs` after it), what waits and how to answer it, what was
    written — and the last line `Чекають рішення: N · змінено записів: M`.
    A pass that changed nothing, with nothing waiting or held, is the header and the one line "без змін" — and under
    it the blocks that could not be checked ("·", such as a team block whose core folder is not here) and those whose
    source lags behind your base ("=", with its note)."""
    p = res["plan"]
    lines = render_plan(p).splitlines()[:-1]            # the plan's last line speaks of what would change
    held = res.get("held") or {}
    if not (res["changed"] or res["pending"] or res["errors"] or res["ignored"] or held):
        return "\n".join([lines[0], "без змін"] + ["%s  %s  %s" % (r["sign"], clip(r["block"], HEADER_CLIP), clip(r["note"], NOTE_CLIP))
                                                  for r in p["rows"] if r["sign"] == SKIPPED or r.get("behind")])
    for x in res["errors"][len(p["errors"]):]:
        lines.append("помилка: %s — %s" % (clip(x["block"] or "?", HEADER_CLIP), clip(x["why"], HEADER_CLIP)))
    for bid, sign in res["ignored"].items():
        if sign == "!":
            lines.append("не застосовано: --choose/--add %s — у блоку зламані маркери (рядок «помилка» вище)" % clip(bid, HEADER_CLIP))
        else:
            lines.append("не потрібне: --choose/--add %s — знак %s" % (clip(bid, HEADER_CLIP), sign))
    rejected = {r["block"] for r in p["rows"] if r.get("rejected")}
    for bid, sign in held.items():
        lines.append("утримано: %s %s — цей прохід його не чіпав" % (sign, clip(bid, HEADER_CLIP))
                     + (" · взяти текст ядра: --choose %s=theirs" % clip(bid, HEADER_CLIP) if bid in rejected else ""))
    signs = {r["block"]: r["sign"] for r in p["rows"]}
    gone = {r["block"] for r in p["rows"] if r["source"] is None and r["sign"] in ("⚠", "?")}
    for bid in res["pending"]:
        how = "--add %s" % bid if signs[bid] == "+" else "--choose %s=theirs|mine%s" % (bid, "" if bid in gone else "|both")
        lines.append("чекає рішення: %s %s — %s" % (signs[bid], clip(bid, HEADER_CLIP), clip(how, NOTE_CLIP)))
    if res["changed"]:
        lines.append("записано: %s · знімок %s (назад: ctx undo)" % (", ".join(res["written"]) or "лише стан блоків", res["snapshot"]))
    else:
        lines.append("записів не змінено")
    lines.append("Чекають рішення: %d · змінено записів: %d" % (len(res["pending"]), len(res["written"])))
    return "\n".join(lines)
