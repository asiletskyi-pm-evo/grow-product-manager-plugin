#!/usr/bin/env python3
"""Grow PM — PreToolUse write gate (since v2.6.0).

Runs before createJiraIssue / editJiraIssue / createConfluencePage /
updateConfluencePage on any connector. It does NOT judge the artifact — a hook
sees only the tool call, never the conversation (hooks reference: prompt/command
hooks receive the hook input JSON). What it can do deterministically is put a
human in the loop before an irreversible write, with the checklist the artifact
quality gate expects to have been completed by then:

  permissionDecision: "ask" → the host shows the reason and waits for the user.

Since v3.10.0 it also runs before Write / Edit / MultiEdit / NotebookEdit: a
file under a registered shared-context provider's local folder, outside the
folder's `writable` globs, gets the same "ask" with the reason and the
alternative (references/context-provider-protocol.md §7). Everything else
passes silently.

Since v3.14.0 the registrations are read within 3 s each and 6 s for all; one that is
not read in time (iCloud has not downloaded it) gets the "ask" too, naming it — the
target may lie in its folder.

Since v4.0.0 a Write / Edit / MultiEdit of a note in a vault of local-context.md that
changes a generated region (scripts/ctx_regions.py — references/vault-schema.md,
Generated regions) gets the "ask" too: a region belongs to its script, which rewrites
it. local-context.md and the records of the context store are not the gate's (a
human edit inside a provider's block is kept there, context-provider-protocol.md §12);
a file iCloud has not downloaded, or over 2 MB, is not read.

Metadata-only edits (status, labels, title) pass silently. The gate is opt-out:
`/grow-product-manager:setup --write-gate off` writes {"write_gate": "off"} to
the plugin data dir. Fail open: any error → exit 0, no output (= allow).
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

CONTENT_KEYS = ("description", "body", "content", "bodyContent", "value", "text")
FILE_TOOLS = ("Write", "Edit", "MultiEdit", "NotebookEdit")
MIN_CONTENT = 200  # characters — below this an edit is metadata, not an artifact


def config_paths():
    out = []
    d = os.environ.get("CLAUDE_PLUGIN_DATA")
    if d:
        out.append(os.path.join(d, "config.json"))
    out.append(os.path.join(os.path.expanduser("~"), ".grow-pm", "plugin-data", "config.json"))
    return out


def write_gate_enabled():
    for p in config_paths():
        try:
            with open(p, encoding="utf-8") as f:
                cfg = json.load(f)
            if str(cfg.get("write_gate", "on")).lower() in ("off", "false", "0"):
                return False
            return True
        except Exception:
            continue
    return True


def content_size(obj):
    """Longest content-like string anywhere in tool_input."""
    best = 0
    stack = [obj]
    while stack:
        cur = stack.pop()
        if isinstance(cur, dict):
            for k, v in cur.items():
                if isinstance(v, str) and any(c in k.lower() for c in CONTENT_KEYS):
                    best = max(best, len(v))
                elif isinstance(v, (dict, list)):
                    stack.append(v)
        elif isinstance(cur, list):
            stack.extend(cur)
    return best


_CONTEXT = {}


def context_text(cwd=None):
    """Read once per run (review M-8) — see _context_text."""
    if cwd not in _CONTEXT:
        _CONTEXT[cwd] = _context_text(cwd)
    return _CONTEXT[cwd]


def _context_text(cwd=None):
    """The user's local-context.md: the digest's path, the canonical store, then every place the
    SessionStart digest searches (connected folders in hosted sessions, the working directory)."""
    cands = [os.environ.get("GROW_PM_CONTEXT_PATH"), os.path.join(os.path.expanduser("~"), ".grow-pm", "local-context.md")]
    try:
        import session_start
        cands += session_start.candidates(cwd or os.getcwd())
    except Exception:
        pass
    for p in cands:
        if p and os.path.isfile(p):
            with open(p, encoding="utf-8", errors="replace") as f:
                return f.read()
    return ""


def provider_hit(tool_input, cwd=None):
    """(the provider registration whose read-only folder holds the target or None, the target, [the registrations not
    read in time]). Since v3.14 the registrations are read on the boundary's budget — 3 s each, 6 s for all
    (`cc.boundary_registrations`) — so a registration iCloud has not downloaded never holds the write past the hook's
    timeout; it is named instead, and the caller asks, since the target may be in its folder."""
    path = str(tool_input.get("file_path") or tool_input.get("notebook_path") or "")
    if not path:
        return None, "", []
    if not os.path.isabs(os.path.expanduser(path)) and cwd:
        path = os.path.join(cwd, path)           # the hook input's cwd, not this process's
    import ctx_common as cc
    text = context_text(cwd)
    regs, late = cc.boundary_registrations(cc.vault_entries(text) if text else [])
    return cc.boundary_hit(path, regs), path, late


REGION_MAX = 2_000_000


def region_hit(tool, tool_input, cwd=None, text=None):
    """(the region a write would change as «<ns> id=<id>» — or «a region marker» —, the path) or (None, path): a .md
    note inside a vault of local-context.md, not local-context.md, not under a store's `_System/context/`, on disk,
    downloaded and not over REGION_MAX; an Edit / MultiEdit whose old text lies on a region, or a Write whose new text
    changes the note's regions."""
    import ctx_common as cc
    import ctx_regions as rg
    path = str(tool_input.get("file_path") or "")
    if not path or not path.lower().endswith(".md") or os.path.basename(path).lower() == "local-context.md":
        return None, path
    if not os.path.isabs(os.path.expanduser(path)) and cwd:
        path = os.path.join(cwd, path)
    real = os.path.realpath(os.path.expanduser(path))
    text = context_text(cwd) if text is None else text
    inside = False
    fold = lambda p_: cc.N(p_).casefold()        # APFS: one file under NFC and NFD, any case (review M-6)
    for vault, _folder in cc.vault_entries(text):
        root = os.path.realpath(os.path.expanduser(vault))
        if fold(real) == fold(root) or fold(real).startswith(fold(root) + os.sep):
            inside = True
            rel = fold(real)[len(fold(root)):].replace(os.sep, "/")
            if "/_system/context/" in rel:
                return None, path
    if not inside or not os.path.isfile(real):
        return None, path
    try:
        info = os.stat(real)
        if getattr(info, "st_flags", 0) & 0x40000000 or info.st_size > REGION_MAX:
            return None, path
        with open(real, encoding="utf-8", errors="replace") as f:
            old = f.read()
    except OSError:
        return None, path
    regions, _ = rg.parse(old)
    if not regions and "<!--" not in old:
        return None, path

    def name(snippet):
        for r in regions:
            i = old.find(snippet)
            while i >= 0:
                if i < r["end"] and i + len(snippet) > r["start"]:
                    return "%s id=%s" % (r["ns"], r["id"]) if r["id"] else r["ns"]
                i = old.find(snippet, i + 1)
        return "a region marker"

    if tool == "Write":
        new = str(tool_input.get("content") or "")
        if rg.changed(old, new):
            gone = [r for r in regions if (r["ns"], r["id"], r["inner"]) not in
                    {(x["ns"], x["id"], x["inner"]) for x in rg.parse(new)[0]}]
            return ("%s id=%s" % (gone[0]["ns"], gone[0]["id"]) if gone and gone[0]["id"] else
                    gone[0]["ns"] if gone else "a region marker"), path
        return None, path
    edits = tool_input.get("edits") if tool == "MultiEdit" else [tool_input]
    cur = old
    for e in edits or []:                        # the edits in sequence (review M-7), on a copy of the note
        snippet, repl = str((e or {}).get("old_string") or ""), str((e or {}).get("new_string") or "")
        if snippet:
            cur = cur.replace(snippet, repl) if (e or {}).get("replace_all") else cur.replace(snippet, repl, 1)
    if rg.changed(old, cur):                     # only a write that changes a region asks (final review I2: an append
        for e in edits or []:                    # after the end marker leaves every region as it was)
            snippet = str((e or {}).get("old_string") or "")
            if snippet and rg.touches(old, snippet):
                return name(snippet), path
        return "a region", path
    return None, path


def ask(reason):
    print(json.dumps({"hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "permissionDecision": "ask",
        "permissionDecisionReason": reason,
    }}))


def main():
    raw = sys.stdin.read()
    data = json.loads(raw) if raw.strip() else {}
    tool = str(data.get("tool_name", ""))
    tool_input = data.get("tool_input") or {}
    if not tool or not write_gate_enabled():
        return
    if tool in FILE_TOOLS:
        hit, path, late = provider_hit(tool_input, data.get("cwd"))
        if hit:
            ask("Grow PM provider boundary: %s is inside the local folder of the shared-context provider "
                "'%s', which is read-only for this plugin (references/context-provider-protocol.md §7). "
                "Write the note in your own vault layer instead, or record a correction in your overlay "
                "note for this provider; confirm only if you mean to edit the provider's copy. "
                "Disable with /grow-product-manager:setup --write-gate off." % (path, hit.get("title") or hit.get("id")))
        elif late:
            ask("Grow PM provider boundary: a shared-context provider registration could not be read: %s — not available "
                "locally (still downloading?), so whether %s is inside a provider's read-only folder cannot be checked "
                "(references/context-provider-protocol.md §7). Confirm only if it is not; or wait until the registration "
                "has downloaded and try again. Disable with /grow-product-manager:setup --write-gate off."
                % (", ".join(late), path))
        elif tool in ("Write", "Edit", "MultiEdit"):
            region, path = region_hit(tool, tool_input, data.get("cwd"))
            if region:
                ask("Grow PM generated region: this write changes %s in %s — text its script writes and rewrites on its "
                    "next run (references/vault-schema.md, Generated regions). Change the source and re-run the "
                    "generator (`ctx vault normalize` for the ctx regions), or write outside the markers; confirm only if "
                    "you mean to edit the region by hand. Disable with /grow-product-manager:setup --write-gate off."
                    % (region, path))
        return
    op = tool.rsplit("__", 1)[-1]
    if op not in ("createJiraIssue", "editJiraIssue", "createConfluencePage", "updateConfluencePage"):
        return  # not a gated operation (defensive: the matcher should already exclude it)
    if op in ("editJiraIssue", "updateConfluencePage") and content_size(tool_input) < MIN_CONTENT:
        return  # metadata-only edit — no prompt
    target = "Jira issue" if "Jira" in op else "Confluence page"
    verb = "create" if op.startswith("create") else "update"
    reason = (
        "Grow PM write gate: about to %s a %s via %s. Before confirming, check the chat for: "
        "(1) the artifact quality gate report line (\"checker: …\" / maker–checker findings applied) — "
        "references/artifact-style-gate.md; (2) your explicit go-ahead to publish this artifact; "
        "(3) that this is the intended space/project, not a sandbox. "
        "Disable this prompt with /grow-product-manager:setup --write-gate off."
        % (verb, target, tool)
    )
    ask(reason)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass
    sys.exit(0)
