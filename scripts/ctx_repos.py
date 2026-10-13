#!/usr/bin/env python3
"""Grow PM — the repositories a product draws context blocks from (since v3.13.0).

A repository is one provider registration (`{vault}/{plugin_folder}/_System/providers/<id>.yaml`,
or `~/.grow-pm/providers/<id>.yaml`; schema `provider-registration/1` or `/2`,
references/context-provider-protocol.md §3b). `load_repos` reads them through
`ctx_common.find_registrations` and gives every one the same shape, with defaults, so the code
that fetches blocks never branches on the schema version.

Reads local files only — no network, nothing written. Stdlib only.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ctx_common as cc  # noqa: E402

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
    if isinstance(v, str) and v.strip().lstrip("-").isdigit():
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
    elif kind == "bundle" and paths:
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
