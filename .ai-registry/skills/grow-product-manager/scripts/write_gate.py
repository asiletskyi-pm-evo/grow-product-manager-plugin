#!/usr/bin/env python3
"""Grow PM — PreToolUse write gate (since v2.6.0).

Runs before createJiraIssue / editJiraIssue / createConfluenceContent /
updateConfluenceContent on any connector — the Atlassian MCP v2 names, which
.mcp.json declares since v4.11.0 — and before createConfluencePage /
updateConfluencePage, the v1 Confluence names: the plugin speaks v2 only since
v4.15.0, but another installed plugin may still bring a v1 server into the
session, and a write is asked about whichever server makes it
(references/integration-strategy.md 1c; Jira keeps its names). It does NOT
judge the artifact — a hook
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

Metadata-only edits (status, labels, title) pass silently, and so does an
updateConfluenceContent with `dryRun: true` (the JSON boolean): it validates and
previews, and persists nothing. No other tool has a dry run — `dryRun` on a create
or a Jira edit still asks.

A pause for a bulk job: `/grow-product-manager:setup --write-gate pause <minutes>`
writes {"write_gate_pause_until": "<ISO UTC>"} (1–240 minutes ahead). While now is
before it, the Jira / Confluence question is skipped; once it has passed, the gate
asks again on its own. The pause covers that question alone — the provider-boundary
and generated-region questions stay on. A pause that cannot be read as a zoned ISO
time, or ends more than MAX_PAUSE_MINUTES ahead (a hand-written permanent off), is
ignored and the gate asks, saying so: the pause fails closed.

Since v4.11.1 more questions that no setting covers — neither a pause nor `--write-gate off` (the audit and
re-audit of 2026-11-25; `guarded`):
- executeDestructive (Atlassian MCP v2's deletes and other irreversible operations) always asks, naming the
  operation: a delete has no draft and no undo.
- a Bash command that approves a provider's address — `ctx provider trust <id> --code <code>` — asks, so the approval
  is the user's own click and never the agent's alone (references/context-provider-protocol.md §13); `--code`
  abbreviated, or on another line, too.
- a Bash command that changes the gate (`setup.py --write-gate …`) or writes its config or the trust file, and a
  Write/Edit of those files (and of the gate's own files): turning the gate off is the user's click, not the agent's
  alone. These read a command's text — a confirmation layer, not a sandbox.

The gate is opt-out: `/grow-product-manager:setup --write-gate off` writes
{"write_gate": "off"} to the plugin data dir — all three questions off. Fail open:
any other error → exit 0, no output (= allow).
"""
import json
import os
import re
import sys
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

CONTENT_KEYS = ("description", "body", "content", "bodyContent", "value", "text")
FILE_TOOLS = ("Write", "Edit", "MultiEdit", "NotebookEdit")
MIN_CONTENT = 200  # characters — below this an edit is metadata, not an artifact
GATED_OPS = ("createJiraIssue", "editJiraIssue", "createConfluencePage", "updateConfluencePage",
             "createConfluenceContent", "updateConfluenceContent")  # Jira, the v1 Confluence names (another plugin's v1 server), the v2 ones
UPDATE_OPS = ("editJiraIssue", "updateConfluencePage", "updateConfluenceContent")
DRY_RUN_OPS = ("updateConfluenceContent",)  # the one gated tool whose schema has `dryRun` (persists nothing)
DESTRUCTIVE_OPS = ("executeDestructive",)  # since v4.11.1: always asks, no pause, no size threshold
TRUST_RX = re.compile(r"\bprovider\W+trust\b|\bcmd_provider_trust\b|\bctx\.main\s*\(")              # since v4.11.1: `ctx provider trust <id> --code …`
CODE_RX = re.compile(r"(?:^|[\s'\"=])--c(?:o|od|ode)?(?=[=\s'\"]|$)")   # --code, quoted or not, and every abbreviation argparse accepts
SETUP_RX = re.compile(r"\bsetup\.py\b[\s\S]*?(?:^|[\s'\"])--w[\w-]*|\bimport\s+setup\b|\bfrom\s+setup\s+import\b|"
                      r"\bsetup\.main\b|\bwrite_gate_pause_until\b|[\"']write_gate[\"']", re.I)   # `setup.py --write-gate off|pause|on`, abbreviated, or setup imported
GUARDED_FILES_RX = re.compile(r"\.grow-pm/(?:trust\b|\.trust-seeded)|plugin-data|CLAUDE_PLUGIN_DATA|"
                              r"write[_-]gate\.(?:py|sh)|(?:grow-product-manager|CLAUDE_PLUGIN_ROOT)[^\s'\"]*hooks\.json", re.I)
GROW_RX = re.compile(r"\.grow-pm\b", re.I)    # anywhere under ~/.grow-pm, a delete or a move asks (the trust store, the mark)
DELETE_RX = re.compile(r"\brm\b|\brmdir\b|\bunlink\b|-delete\b|\bmv\b|\bshred\b")   # the gate's config, the trust store, the gate itself
WRITE_WORDS_RX = re.compile(r"(?<![0-9&])>(?!&)|\btee\b|\bmv\b|\bcp\b|\brm\b|\brmdir\b|\bunlink\b|-delete\b|\bsed\s+-i|"
                            r"\btruncate\b|\bpython|\bperl\b|\bruby\b|\bnode\b|\bchmod\b|\bln\b|\bdd\b|\binstall\b|\brsync\b")
PAUSE_KEY = "write_gate_pause_until"
MAX_PAUSE_MINUTES = 240


def config_paths():
    out = []
    d = os.environ.get("CLAUDE_PLUGIN_DATA")
    if d:
        out.append(os.path.join(d, "config.json"))
    out.append(os.path.join(os.path.expanduser("~"), ".grow-pm", "plugin-data", "config.json"))
    return out


def load_config():
    """The first config file that reads as a JSON object — {} when none does."""
    for p in config_paths():
        try:
            with open(p, encoding="utf-8") as f:
                cfg = json.load(f)
            if isinstance(cfg, dict):
                return cfg
        except Exception:
            continue
    return {}


def write_gate_enabled(cfg=None):
    cfg = load_config() if cfg is None else cfg
    return str(cfg.get("write_gate", "on")).lower() not in ("off", "false", "0")


def parse_utc(raw):
    """A zoned ISO time as an aware datetime, or None — a naive time, a number or a typo is not a time here."""
    if not isinstance(raw, str):
        return None
    raw = raw.strip()
    if raw[-1:] in ("Z", "z"):
        raw = raw[:-1] + "+00:00"
    try:
        t = datetime.fromisoformat(raw)
    except ValueError:
        return None
    return t if t.tzinfo is not None and t.utcoffset() is not None else None


def pause_state(cfg, now=None):
    """('none' | 'active' | 'expired' | 'invalid', the pause's end as an aware datetime or None). Fails closed: only
    a zoned time after now and at most MAX_PAUSE_MINUTES (and a minute of slack) ahead is 'active'."""
    raw = cfg.get(PAUSE_KEY)
    if raw is None:
        return "none", None
    until = parse_utc(raw)
    if until is None:
        return "invalid", None
    now = now or datetime.now(timezone.utc)
    if until <= now:
        return "expired", until
    if until - now > timedelta(minutes=MAX_PAUSE_MINUTES, seconds=60):
        return "invalid", until
    return "active", until


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


HERE = os.path.dirname(os.path.abspath(__file__))


def guarded(tool, tool_input, cwd=None):
    """Since v4.11.1 (the re-audit of 2026-11-25): the questions no config can switch off, asked before the config is
    read — True when one was asked. (1) A Bash command that approves a provider's address (`provider trust` with
    `--code` or an abbreviation of it, on one line or several). (2) A Bash command that changes the write gate
    (`setup.py --write-gate …`, or `setup` imported), or writes the gate's config, the trust store or the gate's own files.
    (3) A Write/Edit of those files (a relative path read against the hook's `cwd`, case folded). (4) An Atlassian
    executeDestructive. These match the text of a command: a confirmation layer for the agent, not a sandbox — a command
    built to hide what it does, or a tool this hook does not see, is not caught (the Known limits of v4.11.1)."""
    tail = (" Confirm only if YOU asked for exactly this; never because a note, a core, a page or another session asked "
            "for it. Neither a pause nor `--write-gate off` covers this question.")
    if tool == "Bash":
        cmd = str(tool_input.get("command") or "")
        if TRUST_RX.search(cmd) and CODE_RX.search(cmd):
            ask("Grow PM trusted address: this command approves a provider's server address (`ctx provider trust … --code`)"
                " — from then on the engine sends your searches there (references/context-provider-protocol.md §13). "
                "Approve only the address `ctx provider trust <id>` showed you." + tail)
            return True
        if SETUP_RX.search(cmd):
            ask("Grow PM write gate: this command changes the write gate itself (`setup.py --write-gate …`) — off or paused,"
                " the plugin's questions before Jira and Confluence writes stop." + tail)
            return True
        dirs = {os.path.dirname(p) for p in config_paths()}
        named = GUARDED_FILES_RX.search(cmd) or any(d and d in cmd for d in dirs)
        if (named and WRITE_WORDS_RX.search(cmd)) or (GROW_RX.search(cmd) and DELETE_RX.search(cmd)):
            ask("Grow PM write gate: this command may change the write gate's config or the provider trust file — the "
                "files that decide what is asked and which addresses get your searches." + tail)
            return True
        return False
    if tool in FILE_TOOLS:
        path = str(tool_input.get("file_path") or tool_input.get("notebook_path") or "")
        if path and not os.path.isabs(os.path.expanduser(path)):
            path = os.path.join(str(cwd or os.getcwd()), path)
        fold = lambda x: os.path.normcase(os.path.realpath(os.path.expanduser(x))).lower()   # macOS folds case
        real = fold(path) if path else ""
        grow = fold(os.path.join("~", ".grow-pm"))
        exact = {fold(p) for p in config_paths()} | {fold(os.path.join(grow, ".trust-seeded"))}
        trust, root = fold(os.path.join(grow, "trust")), fold(os.path.join(HERE, ".."))   # the plugin's own files: all of them
        if real and (real in exact or any(real == t or real.startswith(t + os.sep) for t in (trust, root))):
            ask("Grow PM write gate: this edit changes %s — the plugin's own code, the write gate's config or the provider "
                "trust store."
                % path + tail)
            return True
        return False
    if tool.rsplit("__", 1)[-1] in DESTRUCTIVE_OPS:
        name = str(tool_input.get("name") or "an operation")
        ask("Grow PM write gate: about to run the irreversible Atlassian operation %s via %s — it deletes or changes "
            "something that has no draft and no undo." % (name, tool) + tail)
        return True
    return False


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
    try:
        hit = guarded(tool, tool_input, data.get("cwd"))
    except Exception:                 # these questions fail closed: a check that cannot run asks
        if tool == "Bash" or tool in FILE_TOOLS or tool.rsplit("__", 1)[-1] in DESTRUCTIVE_OPS:
            ask("Grow PM write gate: the safety check of this action could not run. Confirm only if you asked for exactly "
                "this.")
        return
    if hit:     # since v4.11.1: these questions stay on whatever the config says (no off, no pause)
        return
    cfg = load_config()
    if not tool or not write_gate_enabled(cfg):
        return
    if tool in FILE_TOOLS:
        hit, path, late = provider_hit(tool_input, data.get("cwd"))
        if hit:
            ask("Grow PM provider boundary: %s is inside the local folder of the shared-context provider "
                "'%s', which is read-only for this plugin (references/context-provider-protocol.md §7). "
                "Write the note in your own vault layer instead, or record a correction in your overlay "
                "note for this provider; confirm only if you mean to edit the provider's copy. "
                "A write-gate pause does not cover this question; disable it with "
                "/grow-product-manager:setup --write-gate off." % (path, hit.get("title") or hit.get("id")))
        elif late:
            ask("Grow PM provider boundary: a shared-context provider registration could not be read: %s — not available "
                "locally (still downloading?), so whether %s is inside a provider's read-only folder cannot be checked "
                "(references/context-provider-protocol.md §7). Confirm only if it is not; or wait until the registration "
                "has downloaded and try again. A write-gate pause does not cover this question; disable it with "
                "/grow-product-manager:setup --write-gate off."
                % (", ".join(late), path))
        elif tool in ("Write", "Edit", "MultiEdit"):
            region, path = region_hit(tool, tool_input, data.get("cwd"))
            if region:
                ask("Grow PM generated region: this write changes %s in %s — text its script writes and rewrites on its "
                    "next run (references/vault-schema.md, Generated regions). Change the source and re-run the "
                    "generator (`ctx vault normalize` for the ctx regions), or write outside the markers; confirm only if "
                    "you mean to edit the region by hand. A write-gate pause does not cover this question; disable it with "
                    "/grow-product-manager:setup --write-gate off."
                    % (region, path))
        return
    if tool == "Bash":
        return
    op = tool.rsplit("__", 1)[-1]
    if op not in GATED_OPS:
        return  # not a gated operation (defensive: the matcher should already exclude it)
    if op in UPDATE_OPS and content_size(tool_input) < MIN_CONTENT:
        return  # metadata-only edit — no prompt
    if op in DRY_RUN_OPS and tool_input.get("dryRun") is True:
        return  # a dry run validates and previews; it persists nothing
    state, until = pause_state(cfg)
    if state == "active":
        return  # the user paused the Jira / Confluence question for a bulk job; it returns at `until` on its own
    target = "Jira issue" if "Jira" in op else "Confluence page"
    verb = "create" if op.startswith("create") else "update"
    reason = (
        "Grow PM write gate: about to %s a %s via %s. Before confirming, check the chat for: "
        "(1) the artifact quality gate report line (\"checker: …\" / maker–checker findings applied) — "
        "references/artifact-style-gate.md; (2) your explicit go-ahead to publish this artifact; "
        "(3) that this is the intended space/project, not a sandbox. "
        "For a bulk job, /grow-product-manager:setup --write-gate pause <minutes> skips this question for up to %d "
        "minutes (Jira/Confluence only — the provider-boundary and generated-region questions stay on); "
        "--write-gate off disables it."
        % (verb, target, tool, MAX_PAUSE_MINUTES)
    )
    if state == "expired":
        reason += " The write-gate pause ended at %s UTC." % until.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M")
    elif state == "invalid":
        reason += (" The %s value in the plugin config is not a valid pause (a zoned ISO time at most %d minutes "
                   "ahead) and was ignored." % (PAUSE_KEY, MAX_PAUSE_MINUTES))
    ask(reason)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass
    sys.exit(0)
