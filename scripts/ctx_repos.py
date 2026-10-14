#!/usr/bin/env python3
"""Grow PM — the repositories a product draws context blocks from (since v3.13.0).

A repository is one provider registration (`{vault}/{plugin_folder}/_System/providers/<id>.yaml`,
or `~/.grow-pm/providers/<id>.yaml`; schema `provider-registration/1` or `/2`,
references/context-provider-protocol.md §3b). `load_repos` reads them through
`ctx_common.find_registrations` and gives every one the same shape, with defaults, so the code
that fetches blocks never branches on the schema version.

`fetch` reads a repository's blocks ("theirs") from its MCP server or from its core folder; the registrations
themselves are read from local files only. Nothing is ever written. Stdlib only.
"""
import collections
import contextlib
import datetime
import io
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ctx_common as cc  # noqa: E402
import ctx_mcp as cm  # noqa: E402
import ctx_store as cs  # noqa: E402
import provider_bundle as pb  # noqa: E402

RANKS = {"personal": 100, "team": 500, "org": 1000}     # a higher rank wins when two repositories disagree
DEFAULT_AUTHORITY = "org"                               # what the bundle builder writes
FALLBACK_RANK = RANKS["team"]                           # an authority that is none of the three
BLOCK_SOURCES = ("auto", "mcp", "paths")
ENDPOINT_KEYS = ("url", "root", "headers_env")


def _s(v):
    """A scalar as text; nothing, a list or a mapping as ''."""
    return "" if v is None or isinstance(v, (list, dict)) else str(v).strip()


def _list(v):
    """A list of texts: a list as it is, a lone value as a one-item list, nothing as []."""
    if isinstance(v, list):
        return [_s(x) for x in v if _s(x)]
    return [_s(v)] if _s(v) else []


def _rank(v, authority):
    """The explicit rank when it is a whole number (quoted or not), else the authority's."""
    if isinstance(v, int) and not isinstance(v, bool):
        return v
    if isinstance(v, str) and re.fullmatch(r"-?[0-9]+", v.strip()):    # not isdigit(): "²" passes it, int() rejects it
        return int(v.strip())
    return RANKS.get(authority, FALLBACK_RANK)


def normalise(reg):
    """A registration as read by `find_registrations` → the repository dict (schema v1 or v2)."""
    out = dict(reg)                                     # access, mode, contract, index, source_version, writable …
    rid = _s(reg.get("id"))
    authority = _s(reg.get("authority")) or DEFAULT_AUTHORITY
    paths = list(reg.get("paths") or [])
    kind = _s(reg.get("kind"))
    core_root = _s(reg.get("core_root"))
    if core_root:
        core_root = os.path.normpath(os.path.expanduser(cc.N(core_root)))
    elif kind in ("bundle", "folder") and paths:       # a folder's path is the core itself; an mcp repository has none
        core_root = paths[0]
    ep = reg.get("endpoint") if isinstance(reg.get("endpoint"), dict) else {}
    source = _s(reg.get("blocks_source")).lower()
    out.update({
        "id": rid,
        "title": _s(reg.get("title")) or rid,
        "kind": kind,
        "namespace": _s(reg.get("namespace")) or rid,
        "blocks_file": _s(reg.get("blocks_file")),
        "core_root": core_root,
        "paths": paths,
        "products": _list(reg.get("products")),
        "rank": _rank(reg.get("rank"), authority),
        "authority": authority,
        "endpoint": {k: _s(ep.get(k)) for k in ENDPOINT_KEYS},
        "blocks_source": source if source in BLOCK_SOURCES else "auto",
        "home_record": _s(reg.get("home_record")),
        "skip_blocks": _list(reg.get("skip_blocks")),
        "team": _s(reg.get("team")),
        "role": _s(reg.get("role")),
        "jira_write": _s(reg.get("jira_write")),
        "status": _s(reg.get("status")) or "active",
        "synced_at": _s(reg.get("synced_at")),
        "access": _s(reg.get("access")),
        "source_version": _s(reg.get("source_version")),
        "_file": reg.get("_file", ""),
    })
    return out


def load_repos(context_text, home, extra_dirs=None, skipped=None):
    """Every registered repository, normalised, in registration order — the vaults' providers folders
    first, then `<home>/.grow-pm/providers` (or `extra_dirs` when given, as in find_registrations;
    the home is never taken from the environment). An id seen twice keeps the first. Unreadable
    registrations are left out and, when `skipped` is a list, appended to it as (path, reason)."""
    dirs = [os.path.join(home, ".grow-pm", "providers")] if extra_dirs is None else list(extra_dirs)
    regs = cc.find_registrations(cc.vault_entries(context_text), extra_dirs=dirs, skipped=skipped)
    return [normalise(r) for r in regs]


# ------------------------------------------------------------------ fetch
NOTE_TOOL = "vault_get_note"        # the one MCP tool a fetch calls; it is on cm.ALLOWED
MAX_ERROR = 300


def _stamp(now):
    """`now` (a datetime, or text taken as it is; None → the present moment) as ISO text with the offset."""
    if isinstance(now, str):
        return now
    t = now if isinstance(now, datetime.datetime) else datetime.datetime.now()
    if t.tzinfo is None:
        t = t.astimezone()
    return t.isoformat(timespec="seconds")


def _clean(text):
    """A message that came from a server, on one line: control characters gone, length bounded."""
    return re.sub(r"[\x00-\x1f\x7f]+", " ", str(text)).strip()[:MAX_ERROR]


def _lf(text):
    return text.replace("\r\n", "\n").replace("\r", "\n")


def _read_bounded(path):
    """The text of a file the way `provider_bundle.rd` gives it (universal newlines), but through the store's
    reader: a file iCloud has not downloaded costs the time budget, not a hang."""
    return _lf(cs.read_text(path))


@contextlib.contextmanager
def _bounded_reads():
    prev = pb.READ
    pb.READ = _read_bounded
    try:
        yield
    finally:
        pb.READ = prev


def _unavailable(why):
    """The team error: "team block: not available (<why>)" — a team was due and could not be built, so the plan shows
    the row as "·" and leaves the region you hold alone. `why` is short and names no path."""
    return _clean("team block: not available (%s)" % why)


def _team_why(exc):
    """Why the team block could not be built, in words that carry no secret: a short reason (the file's name, not
    its path; the class of an unexpected exception, not its message), at most MAX_ERROR characters."""
    name = os.path.basename(getattr(exc, "filename", None) or "") if isinstance(exc, OSError) else ""
    if isinstance(exc, cs.StoreError):
        text = str(exc)
    elif isinstance(exc, FileNotFoundError):
        text = "%s not found" % (name or "a file")
    elif isinstance(exc, OSError):
        text = "%s: %s" % (name or "a file", exc.strerror or type(exc).__name__)
    elif isinstance(exc, UnicodeDecodeError):
        text = "a file is not UTF-8 text"
    elif isinstance(exc, json.JSONDecodeError):
        text = "the role model is not valid JSON"
    else:
        text = "unexpected %s" % type(exc).__name__
    return _unavailable(text)


PLACEHOLDER = re.compile(r"^\..+\.icloud$")          # what iCloud leaves of a file it has evicted: `.<name>.icloud`


def _not_downloaded(core_root, manifest):
    """How many files iCloud has evicted where the team block reads: the team-card folder, the people folder and the
    core's templates folder (when the manifest names one) — each read flat, as `provider_bundle.team_context` reads
    them. Its builder takes a card that is not there as optional, so an evicted card would give a degraded block
    that the plan would offer as an update of yours; a count above 0 makes the team block unavailable instead."""
    folders = {os.path.normpath(os.path.join(core_root, manifest.s(k))) for k in ("team_card_dir", "people_dir", "templates_dir")
               if manifest.s(k)}
    count = 0
    for folder in sorted(folders):
        try:
            names = os.listdir(folder)
        except OSError:
            continue
        count += sum(1 for n in names if PLACEHOLDER.match(n))
    return count


def _manifest(core_root):
    """(manifest, why not) of the core's provider manifest as the bundle builder reads it. A manifest that is not there
    (never written, or evicted by iCloud: only its `.icloud` placeholder is), or that cannot be read or parsed, is
    (None, reason) — the reason in the words of `_unavailable`, with no path. The builder's `sys.exit(3)` and its
    message on stdout are not ours: neither leaves this function."""
    buf = io.StringIO()
    try:
        with contextlib.redirect_stdout(buf):
            return pb.load_manifest(core_root), None
    except SystemExit:
        said = buf.getvalue().strip()
        if said.startswith("no provider manifest"):
            return None, _unavailable("no provider manifest in the core")
        detail = said.split("provider-manifest.yaml: ", 1)[1] if "provider-manifest.yaml: " in said else ""
        return None, _unavailable("the provider manifest cannot be parsed" + (": " + detail if detail else ""))
    except Exception as e:
        return None, _team_why(e)


def _team_block(repo, manifest, manifest_why, in_file=False):
    """(the team region, None), (None, None) or (None, why not). The region is what the connect flow builds from the
    core's team card and people, without the final newline.

    (None, None) is "not offered" — the plan then removes a team region you hold — and it is said only when that is
    known: the registration names no team; or the role model was read and does not list the team; or there is no
    core folder in the registration and the blocks file itself carries the team region (`in_file`: the file offers
    it). Whenever a team was due and cannot be built — no core folder in the registration, a core folder not on this
    machine, a provider manifest that is missing (iCloud evicted it), unreadable or unparsable, a role model or a
    card that does not arrive or cannot be read, a card iCloud has evicted (`_not_downloaded`: the builder would
    leave it out and give a degraded block), anything unexpected — it is (None, "team block: not available
    (<why>)"): the plan shows "·" and the region is never touched."""
    team, core_root = repo["team"], repo["core_root"]
    if not team:
        return None, None
    if not core_root:
        return (None, None) if in_file else (None, _unavailable("no core folder in the registration"))
    if not os.path.isdir(core_root):
        return None, _unavailable("core folder not found")
    if manifest is None:
        return None, manifest_why or _unavailable("no provider manifest in the core")
    try:
        bundles = manifest.s("bundles_file") or os.path.join(manifest.s("plugin_folder", "."), "_System", "access-bundles.json")
        model = json.loads(pb.rd(os.path.join(core_root, bundles)))
        teams = model["teams"]
        key = team if team in teams else (team[len("team-"):] if team.startswith("team-") else team)
        if key not in teams:
            return None, None
        evicted = _not_downloaded(core_root, manifest)
        if evicted:
            return None, _unavailable("%d file%s not downloaded — open the core folder in Finder to download them"
                                      % (evicted, "" if evicted == 1 else "s"))
        block = pb.team_context(core_root, manifest, key, teams[key], model, repo["jira_write"] or "ask")[0]
        return block.rstrip("\n"), None
    except (Exception, SystemExit) as e:
        return None, _team_why(e)


def _from_mcp(repo, blocks_file, client_factory):
    """(text, None) of the blocks file as the server serves it, or (None, why not)."""
    ep = repo["endpoint"]
    if not ep["url"]:
        return None, "no endpoint url in the registration"
    if not blocks_file:
        return None, "the registration names no blocks_file"
    hdrs = cm.headers_from_env(ep["headers_env"]) if ep["headers_env"] else {}
    try:
        client = client_factory(ep["url"], headers=hdrs)
        if not client.probe():
            hint = "; %s is not set (or not 'Name: value')" % ep["headers_env"] if ep["headers_env"] and not hdrs else ""
            return None, "MCP unreachable: %s%s" % (_clean(getattr(client, "last_error", "") or "no answer"), hint)
        note = client.call(NOTE_TOOL, {"path": ep["root"] + blocks_file})      # Ruling P1: plain concatenation
    except cm.McpError as e:
        return None, "MCP: %s" % _clean(e)
    except Exception as e:                              # a fetch is an answer or a reason, whatever the server did
        return None, "MCP failed unexpectedly (%s)" % type(e).__name__
    content = note.get("content")
    if isinstance(content, str):
        return _lf(content), None
    why = note.get("error")
    return None, "MCP: %s" % (_clean(why) if isinstance(why, str) and why.strip() else "the note has no text content")


def _from_folder(repo, blocks_file):
    """(text, None) of the blocks file in the core folder, or (None, why not)."""
    root = repo["core_root"]
    if not root:
        return None, "no core folder in the registration"
    if not os.path.isdir(root):
        return None, "core folder not found: %s" % root
    if not blocks_file:
        return None, "neither the registration nor the core's manifest names a blocks_file"
    rel = os.path.normpath(blocks_file)
    if os.path.isabs(blocks_file) or rel == os.pardir or rel.startswith(os.pardir + os.sep):
        return None, "blocks_file points outside the core folder: %s" % blocks_file
    try:
        return _lf(cs.read_text(os.path.join(root, rel))), None
    except cs.StoreError as e:
        return None, str(e)
    except FileNotFoundError:
        return None, "blocks file not found: %s" % blocks_file
    except OSError as e:
        return None, "blocks file not available: %s" % (e.strerror or type(e).__name__)
    except UnicodeDecodeError:
        return None, "blocks file is not UTF-8 text: %s" % blocks_file


def _regions(text, namespace):
    """({id: the whole region, markers included, no final newline}, [v= of each]) for the regions of `namespace`
    in `text`, in file order. An id met twice keeps the first; a region that is never closed is no region."""
    ns = re.escape(namespace)
    rx = re.compile(r"<!--\s*%s:begin\s+id=([A-Za-z0-9_.-]+)([^>]*)-->.*?<!--\s*%s:end\s+id=\1\s*-->" % (ns, ns), re.S)
    blocks, versions = {}, []
    for mo in rx.finditer(text):
        if mo.group(1) in blocks:
            continue
        blocks[mo.group(1)] = mo.group(0)
        v = re.search(r"(?:^|\s)v=([^\s>]+)", mo.group(2))
        versions.append(v.group(1) if v else None)
    return blocks, versions


def fetch(repo, client_factory=cm.McpClient, now=None, include_skipped=False):
    """A repository's blocks ("theirs") — read only, nothing is written anywhere.

    `blocks_source` decides where from: "mcp" asks the server only; "paths" reads the core folder only; "auto"
    asks the server when it answers the handshake and otherwise reads the core folder. A server that answers an
    error, a bad answer or nothing counts as unavailable for this fetch; under "auto" the folder is then tried.
    `include_skipped` keeps the blocks of `skip_blocks` in `blocks` (the plan's `--all` lists them); by default they
    are dropped.

    The server path of the blocks file is `endpoint.root + blocks_file`; in the core folder it is
    `core_root/blocks_file`. A registration that names no blocks_file (a v1 bundle) gets the one in the core's
    provider manifest. Files are read through ctx_store.read_text (the iCloud time budget).

    Returns {source: "mcp"|"folder"|None, version: the v= most blocks carry (the first met on a tie; counted
    before skip_blocks, it is the source's), blocks: {id: region text} without skip_blocks (unless `include_skipped`),
    team: the team region or None, team_source: "folder"|None, team_error: why the team region could not be built, or None,
    error: why no blocks came, or None, checked: ISO time}.
    The team region is built from the core folder alone (the card, the people, the role model), whichever
    source the blocks came from, and only once the blocks have arrived: when `error` is set, team, team_source
    and team_error are all empty. `team` None with `team_error` None means the repository offers no team
    (none in the registration, a team the readable role model does not list, or a team region the blocks file
    carries itself when the registration names no core folder); with
    `team_error` set ("team block: not available (<why>)"), a team was due and could not be built — see `_team_block`:
    a missing core folder or provider manifest is a reason, never "not offered".
    """
    out = {"source": None, "version": None, "blocks": {}, "team": None, "team_source": None, "team_error": None,
           "error": None, "checked": _stamp(now)}
    src, core_root, url = repo["blocks_source"], repo["core_root"], repo["endpoint"]["url"]
    with _bounded_reads():
        blocks_file = repo["blocks_file"]
        manifest, manifest_why = None, None
        if core_root and os.path.isdir(core_root) and (repo["team"] or not blocks_file):
            manifest, manifest_why = _manifest(core_root)
        if not blocks_file and manifest is not None:
            blocks_file = manifest.s("blocks_file")

        text, errors = None, []
        if src == "auto" and not url and not core_root:
            errors.append("the registration has neither an endpoint url nor a core folder")
        else:
            if src == "mcp" or (src == "auto" and url):
                text, why = _from_mcp(repo, blocks_file, client_factory)
                if text is not None:
                    out["source"] = "mcp"
                else:
                    errors.append(why)
            if text is None and src in ("auto", "paths"):
                text, why = _from_folder(repo, blocks_file)
                if text is not None:
                    out["source"] = "folder"
                else:
                    errors.append(why)
        if text is not None:                            # the team is only worth building for a fetch that succeeded
            blocks, versions = _regions(text, repo["namespace"])
            out["team"], out["team_error"] = _team_block(repo, manifest, manifest_why, in_file="team" in blocks)
            out["team_source"] = "folder" if out["team"] is not None else None
    if text is None:
        out["error"] = "; ".join(errors)
        return out
    counts = collections.Counter(v for v in versions if v)
    out["version"] = counts.most_common(1)[0][0] if counts else None
    out["blocks"] = {k: v for k, v in blocks.items() if include_skipped or k not in repo["skip_blocks"]}
    return out
