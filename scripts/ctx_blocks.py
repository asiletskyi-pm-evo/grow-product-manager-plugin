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
kebab-case and nothing else, so it can never name a path outside `.state/blocks/`.

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
import ctx_ops as co  # noqa: E402
import ctx_read as cr  # noqa: E402
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
      the repository's is absent and yours is there — the repository removed the block:
      "?"    there is no base: nothing says yours is the repository's text
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
        return "−" if cs.sha_text(nm) in known else "⚠"
    if behind(mine, theirs, st):
        return "="
    if cs.sha_text(nm) in known:
        return "~"
    if cs.sha_text(nt) in known:
        return "✎"
    return "⚠"


def behind(mine, theirs, st):
    """Does the repository offer an older base of a block whose base yours is? A copy of the source that lags (an MCP
    mirror not updated yet, a folder restored from a backup) would otherwise read as "the repository moved" and an
    apply would take your block a version back. The plan says "=" with a note and apply writes nothing: the base stays."""
    if mine is None or theirs is None or not st or not st.get("base_sha"):
        return False
    nm, nt = norm(mine), norm(theirs)
    if nm == nt:
        return False
    sm, sh = cs.sha_text(nm), cs.sha_text(nt)
    return sm == st["base_sha"] and sh != st["base_sha"] and sh in set(st.get("bases") or ())


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
CONTROLS = re.compile(r"[\x00-\x1f\x7f-\x9f  ]+")
MARKER_LINE = re.compile(r"^\s*<!--\s*[^\s:>]+:(?:begin|end)(?![A-Za-z0-9_:.])[^>]*-->\s*$")
NOTES = {"=": "без змін", "~": "оновлено з репозиторію", "✎": "лишаються ваші правки", "⚠": "змінили обидва — потрібне рішення",
         "+": "новий блок у репозиторії", "−": "репозиторій прибрав блок", "✂": "ви прибрали блок",
         "?": "бази немає — невідомо, хто змінив"}
REMOVED_NOTES = {"⚠": "репозиторій прибрав блок, а у вас правки — theirs прибере, mine лишить текст як ваш",
                 "?": "репозиторій не має цього блоку, а бази немає — theirs прибере, mine лишить текст як ваш"}
REMOVED_LINE = "(репозиторій прибрав цей блок)"
BEHIND_NOTE = "джерело позаду вашої бази"         # a "=" whose source offers an older base of yours (`behind`)
QUESTIONS = ("⚠", "+", "?")                     # the signs that need an answer
REWRITES = ("~", "−")                           # the signs an apply without decisions acts on: it rewrites the record that holds the block


def clip(text, limit):
    """`text` as one line that is safe to print: every run of control characters becomes one space, the ends are
    trimmed, and at most `limit` characters stay (the last is "…" when it was cut). Whatever a server sent goes
    through here before it is printed."""
    one = CONTROLS.sub(" ", "" if text is None else str(text)).strip()
    return one if len(one) <= limit else one[:limit - 1].rstrip() + "…"


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
    or changed)."""
    added, gone = [], set()
    for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(None, base, side, autojunk=False).get_opcodes():
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


def _differences(mine, theirs, base):
    """{"theirs", "mine", "base"}: the first DIFF_LINES lines (blank ones skipped, each clipped to LINE_CLIP) of what
    the repository changed, what you changed and what both started from, all against the base text. Without the base
    text ("base" is None) each side is set against the other. A side whose lines are exactly those it is set against
    and whose version moved says only that: "(лише версія v<a> → v<b>)" — a side that removed lines says nothing new.
    `theirs` None is a block the repository removed: its side says so, and what both said is the base's first lines."""
    m = _body_lines(mine)
    t = None if theirs is None else _body_lines(theirs)
    if base is None:
        said_t = [] if t is None else _changed(m, t)[0]
        said_m, was = (m if t is None else _changed(t, m)[0]), None
        ref_t, ref_m, vref_t, vref_m = m, t, mine, theirs
    else:
        b = _body_lines(base)
        said_t, gone_t = _changed(b, t) if t is not None else ([], set(range(len(b))))
        said_m, gone_m = _changed(b, m)
        was = [b[i] for i in sorted(gone_t | gone_m)]
        ref_t, ref_m, vref_t, vref_m = b, b, base, base

    def first(lines):
        return [c for c in (clip(l, LINE_CLIP) for l in lines if l.strip()) if c][:DIFF_LINES]
    if theirs is None:
        said = [REMOVED_LINE]
    else:
        said = first(said_t) or (_version_only(vref_t, theirs) if t == ref_t else [])
    return {"theirs": said, "mine": first(said_m) or (_version_only(vref_m, mine) if m == ref_m else []),
            "base": None if was is None else first(was)}


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
    removed). A genuine removal of some blocks leaves the others in the file."""
    built = fetched.get("team") is not None or bool(fetched.get("team_error"))
    in_file = fetched.get("blocks") or {}
    based = sorted(b for b, e in state["blocks"].items() if (e.get("base_sha") or e.get("bases")) and b not in skip
                   and not (b == "team" and built))
    if not any(b in mine for b in based) or any(b in in_file for b in based):
        return None
    return ("the blocks file holds none of the %d block%s you have a base for (%s) — a wrong, stale or cut file, "
            "not removals" % (len(based), "" if len(based) == 1 else "s", ", ".join(based)))


def source_lost(store, copies, repo, fetched, now):
    """`_lost` for a repository as the plan would see it — your records (the live view), the state — without raising:
    the command line asks it before the lock, so a lost source stops `provider apply` with nothing written. None also
    for a fetch that failed (that is reported on its own)."""
    if fetched.get("error"):
        return None
    records, _, _ = cr._live_view(store, copies, now)
    mine = find_regions(records, namespace_of(repo, fetched))[0]
    return _lost(load_state(store, repo["id"]), mine, fetched, set(repo.get("skip_blocks") or ()))


def plan(store, copies, repo, fetched, now, all_=False):
    """The plan of one repository: what each of its blocks is in your context against what the repository publishes
    now (`fetched`, from `ctx_repos.fetch` with no `error`; with `all_` it should have been fetched with
    `include_skipped`). Reads only — no lock, nothing written.

    Returns {"repo", "source" ("mcp" | "folder"), "source_label", "version" (the repository's), "base_version" ("—" when no
    block has a base), "rows": [{"block", "sign", "host", "source", "note"}], "questions", "changes", "errors"}.

    The rows are the blocks in your records (the pending edits of local-context.md count: the live view) followed by
    those only the repository offers; a block absent on both sides is none. `host` is the record that holds your
    region (for "✂", the one that held it); `source` where the repository's text came from (None when it has none).
    A "⚠" row also carries `diff`, the lines each side changed against the base (see `_differences`). The signs are
    `classify`'s, and "·" for a block of `skip_blocks` (listed only with `all_`; yours never appears without it) and
    for the team block when it could not be built (its reason is the note) — neither is a question or a change.
    `questions` counts the rows "⚠", "+" and "?"; `changes` the records an apply without decisions would rewrite: the
    distinct hosts of the rows "~" and "−". `errors` are `find_regions`' problems (a block with one has no row).
    A "=" row whose source lags behind your base (`behind`) carries `behind: True` and the note
    "джерело позаду вашої бази (v<theirs> < v<yours>)". A blocks file that holds none of the blocks you have a base for
    is no plan at all: SourceLost (see `_lost`).
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
    bad = {x["block"] for x in problems if x["block"]}
    ids = [b for b in list(mine) + [b for b in theirs if b not in mine] if b not in bad]
    if team_error and "team" not in ids and "team" not in bad:
        ids.append("team")
    rows = []
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
            held = _held(entry, m["text"] if m else None)
            row["sign"] = classify(m["text"] if m else None, t, held)
            row["note"] = REMOVED_NOTES[row["sign"]] if t is None and row["sign"] in REMOVED_NOTES else NOTES[row["sign"]]
            if row["sign"] == "=" and behind(m["text"] if m else None, t, held):
                vm, vt = _marker_version(m["text"]), _marker_version(t)
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
        rows.append(row)
    version = fetched.get("version")
    return {"repo": rid, "source": fetched.get("source"), "source_label": _source_label(repo, fetched.get("source")),
            "version": clip(version, HEADER_CLIP) if version else None,
            "base_version": clip(base_version(state) or "—", HEADER_CLIP), "rows": rows,
            "questions": sum(1 for r in rows if r["sign"] in QUESTIONS),
            "changes": len({r["host"] for r in rows if r["sign"] in REWRITES and r["host"]}),
            "errors": [dict(x) for x in problems if all_ or x["block"] not in skip]}


def _detail_lines(diff):
    """The three lines under a "⚠" row: what the repository says now, what you wrote, what both said before (this
    one only when the base text is there). A side with several changed lines continues on aligned lines."""
    out = []
    for label, key in (("Ядро тепер каже", "theirs"), ("Ви писали", "mine"), ("Раніше обидва казали", "base")):
        lines = diff.get(key)
        if lines is None:
            continue
        head = "    %s: " % label
        out.append(head + (lines[0] if lines else "—"))
        out.extend(" " * len(head) + line for line in lines[1:])
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


def apply(store, copies, home, repo, fetched, choose, add, now):
    """One pass of `repo` over your context, from `fetched` (`ctx_repos.fetch` with no `error`). The caller holds the
    lock and has imported the edits of local-context.md first: with edits still waiting it is refused (co.Refused),
    and nothing is written.

    The signs are `plan`'s — the plan is made here, on the records as they are now (a lost source, SourceLost, stops
    it before anything is written) — and each is acted on (spec B6):
      =   nothing in the records; the base becomes the repository's text when it was not — except when the source lags
          behind your base (`behind`): then the base stays as it is
      ~   the region becomes the repository's text, and so does the base
      ✎   your region stays, the base too
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

    The order: snapshot "provider-apply" → the new base texts → the host records (verified today, source
    "repo:<id>") → the state (checked, source, version; per block v, host, checked) → the base texts nobody refers
    to are pruned → one journal line {op provider-apply, source repo:<id>, from_v, to_v, ids: the records written,
    decisions: {block: sign, or "<sign> <answer>"}, pending, snapshot} → the compiled copies. A pass that changes
    nothing but the time of the check writes the state file alone: no snapshot, no journal line, no record.

    A `choose` value that is not an answer, or a block in `choose` / `add` that the plan does not have → ValueError
    before anything is written; an answer for a block that needs none is left out and listed in `ignored`.

    Returns {"repo", "plan", "applied": {block: sign}, "decisions", "pending": [block], "ignored": {block: sign},
    "errors", "changed": bool, "written": [record ids], "snapshot": folder or None, "compiled": [copies]}.
    """
    if fetched.get("error"):
        raise ValueError("apply needs a repository that was fetched, not one that failed: %s" % fetched["error"])
    choose, add = dict(choose or {}), list(add or [])
    wrong = ["%s=%s" % (b, how) for b, how in choose.items() if how not in CHOICES]
    if wrong:
        raise ValueError("--choose takes BLOCK=theirs|mine|both, not %s" % ", ".join(wrong))
    waiting = co.plan_sync(store, copies)
    if sum(co.pending(waiting).values()) + len(waiting["conflicts"]) + len(waiting["missing"]):
        raise co.Refused("changes to local-context.md or to the records wait to be imported — `ctx sync` first, then apply")
    rid, ns = repo["id"], namespace_of(repo, fetched)
    p = plan(store, copies, repo, fetched, now)
    known = {r["block"] for r in p["rows"]} | {x["block"] for x in p["errors"] if x["block"]}
    unknown = sorted(b for b in set(choose) | set(add) if b not in known)
    if unknown:
        raise ValueError("no block %s in the plan of %s — `ctx provider plan %s` lists them" % (", ".join(unknown), rid, rid))
    records = store.load()
    by_id = {r["id"]: r for r in records}
    mine = find_regions(records, ns)[0]
    theirs = _theirs(fetched)[0]
    old = load_state(store, rid)
    state = copy.deepcopy(old)
    checked, today = fetched.get("checked") or now, now[:10]
    edits, rebased, adds = {}, {}, []
    applied, decisions, pending, ignored, refused = {}, {}, [], {}, []
    for row in p["rows"]:
        bid, sign = row["block"], row["sign"]
        how, wanted = choose.get(bid), bid in add
        if (how and sign not in ("⚠", "?")) or (wanted and sign != "+"):
            ignored[bid] = sign                         # an answer to a question the plan does not ask: dropped
        how = how if sign in ("⚠", "?") else None
        wanted = wanted and sign == "+"
        if sign == SKIPPED:
            continue
        m, t, entry = mine.get(bid), theirs.get(bid), state["blocks"].get(bid)
        if (sign in ("⚠", "?") and not how) or (sign == "+" and not wanted):
            pending.append(bid)
            if entry:
                entry["checked"] = checked
            continue
        gone = t is None and sign in ("⚠", "?")        # the repository removed a block you edited (or never had a base for)
        if gone and how == "both":
            raise ValueError("both is not possible for a block the repository removed: %s — theirs removes it, mine keeps "
                             "your text without its markers" % bid)
        if (sign in ("~", "+") or (sign in ("⚠", "?") and how in ("theirs", "both") and not gone)) and not _sound(t, ns, bid):
            refused.append({"block": bid, "host": row["host"], "why": "the repository's region is not well-formed"})
            continue
        if sign == "−" or gone:
            edits.setdefault(m["host"], {})[bid] = DETACH if gone and how == "mine" else None
            state["blocks"].pop(bid, None)
        elif sign == "✂":
            entry["user_removed"] = entry.get("user_removed") or today
            entry["checked"] = checked
        else:
            if sign == "~" or how == "theirs":
                edits.setdefault(m["host"], {})[bid] = t
            elif how == "both":
                edits.setdefault(m["host"], {})[bid] = _both(t, m["text"])
            elif sign == "+":
                adds.append(bid)
            entry = state["blocks"].setdefault(bid, {"base_sha": None, "bases": [], "v": "", "host": None, "checked": None,
                                                     "user_removed": None})
            if sign != "✎" and not row.get("behind"):       # a source behind your base never moves the base back
                _rebase(entry, t)
                rebased[bid] = t
            entry.update(host=m["host"] if m else None, checked=checked, user_removed=None)
        applied[bid] = sign
        decisions[bid] = "%s %s" % (sign, how) if sign in ("⚠", "?") else sign

    bodies = {}
    for host, ops in edits.items():
        body = by_id[host]["body"]
        spans = _spans(body, ns)
        for bid in sorted(ops, key=lambda b: spans[b][0], reverse=True):   # from the end: earlier offsets stay true
            start, end = spans[bid]
            new = _detach(body[start:end]) if ops[bid] is DETACH else ops[bid]
            body = _cut(body, start, end) if not new else body[:start] + new + body[end:]
        bodies[host] = body
    title = clip(repo.get("title") or rid, HEADER_CLIP)
    new_record = None
    if adds:
        home_id = _home_record(repo, mine, records, title)
        if home_id:
            bodies[home_id] = _at_end(bodies.get(home_id, by_id[home_id]["body"]), ns, [theirs[b] for b in adds])
            for bid in adds:
                state["blocks"][bid]["host"] = home_id
        else:
            new_record = {"text": "## %s\n\n%s\n" % (title, "\n\n".join(theirs[b] for b in adds)), "type": cs._h2_type(title),
                          "title": title, "after": records[-1]["id"] if records else None}
    state.update(checked=checked, source=fetched.get("source"), version=fetched.get("version"))
    res = {"repo": rid, "plan": p, "applied": applied, "decisions": decisions, "pending": pending, "ignored": ignored,
           "errors": [dict(x) for x in p["errors"]] + refused, "written": [], "snapshot": None, "compiled": [],
           "changed": bool(bodies or new_record) or _substance(old) != _substance(state)}
    if not res["changed"]:
        save_state(store, rid, state)                  # the time of the check, and nothing else
        return res
    snap = co.snapshot(store, copies, home, "provider-apply")
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
    prune_bases(store, rid, state)
    store.journal({"ts": now, "op": "provider-apply", "source": source, "from_v": old.get("version") or base_version(old),
                   "to_v": fetched.get("version"), "ids": res["written"], "decisions": decisions, "pending": pending,
                   "snapshot": snap})
    if res["written"]:
        res["compiled"] = co.compile_store(store, copies, now, home, snap)["written"]
    res["snapshot"] = snap
    return res


def render_apply(res):
    """The text of an apply: the plan's table (a "⚠" with its three versions under it), then what was not needed,
    what waits and how to answer it, what was written — and the last line `Чекають рішення: N · змінено записів: M`.
    A pass that changed nothing, with nothing waiting, is the header and the one line "без змін" — and under it the
    blocks that could not be checked ("·", such as a team block whose core folder is not here) and those whose source
    lags behind your base ("=", with its note)."""
    p = res["plan"]
    lines = render_plan(p).splitlines()[:-1]            # the plan's last line speaks of what would change
    if not (res["changed"] or res["pending"] or res["errors"] or res["ignored"]):
        return "\n".join([lines[0], "без змін"] + ["%s  %s  %s" % (r["sign"], clip(r["block"], HEADER_CLIP), clip(r["note"], NOTE_CLIP))
                                                  for r in p["rows"] if r["sign"] == SKIPPED or r.get("behind")])
    for x in res["errors"][len(p["errors"]):]:
        lines.append("помилка: %s — %s" % (clip(x["block"] or "?", HEADER_CLIP), clip(x["why"], HEADER_CLIP)))
    for bid, sign in res["ignored"].items():
        lines.append("не потрібне: --choose/--add %s — знак %s" % (clip(bid, HEADER_CLIP), sign))
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
