#!/usr/bin/env python3
"""Grow PM — SessionStart hook (since v2.6.0).

Finds the user's local-context.md wherever this session can see it and hands
the model a short digest as additionalContext, so Step 0a of
references/local-context-protocol.md becomes a lookup instead of a search.
Also exports GROW_PM_CONTEXT_PATH for later Bash calls via CLAUDE_ENV_FILE.

Design rules (see references/harness-map.md → hooks):
- Fail open. Any exception → exit 0, no output. A hook must never block a session.
- Header only. The digest carries paths, versions, names and flags — never
  URLs, ids, emails or tokens. Skills still parse the file themselves (0c–0h).
- Environment-agnostic. The user's home is a sandbox in hosted sessions; the
  context arrives through a connected folder mounted under $HOME/mnt/<name>/.
"""
import glob
import json
import os
import re
import sys

MAX_LINES = 25


def read_stdin():
    try:
        raw = sys.stdin.read()
        return json.loads(raw) if raw.strip() else {}
    except Exception:
        return {}


def candidates(cwd):
    home = os.path.expanduser("~")
    fixed = [
        os.path.join(home, ".grow-pm", "local-context.md"),
    ]
    globs = [
        os.path.join(home, "mnt", "*", "local-context.md"),
        os.path.join(home, "mnt", "*", ".grow-pm", "local-context.md"),
        os.path.join(home, "mnt", "*", "grow-pm", "local-context.md"),
        "/mnt/user-data/uploads/*/local-context.md",
        "/mnt/user-data/uploads/*/.grow-pm/local-context.md",
    ]
    tail = []
    for base in (cwd, os.environ.get("CLAUDE_PROJECT_DIR")):
        if base:
            tail.append(os.path.join(base, "local-context.md"))
            tail.append(os.path.join(base, ".grow-pm", "local-context.md"))
    out = list(fixed)
    for g in globs:
        out.extend(sorted(glob.glob(g)))
    out.extend(tail)
    seen, uniq = set(), []
    for p in out:
        if p not in seen:
            seen.add(p)
            uniq.append(p)
    return uniq


def plugin_version():
    try:
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        with open(os.path.join(root, ".claude-plugin", "plugin.json"), encoding="utf-8") as f:
            return json.load(f).get("version", "?")
    except Exception:
        return "?"


def parse(path):
    """Header-level facts only."""
    with open(path, encoding="utf-8", errors="replace") as f:
        text = f.read()
    facts = {}
    m = re.search(r"^> Configurator version:\s*(\S+)", text, re.M)
    facts["configurator_version"] = m.group(1) if m else "unknown"
    m = re.search(r"^> Generated:.*?Updated:\s*([0-9]{4}-[0-9]{2}-[0-9]{2})", text, re.M)
    facts["updated"] = m.group(1) if m else "unknown"
    m = re.search(r"^- \*\*Language:\*\*\s*([a-z]{2})\b", text, re.M)
    facts["language"] = m.group(1) if m else "unknown"
    m = re.search(r"^- \*\*Mode:\*\*\s*(basic|extended)\b", text, re.M)
    facts["onboarding_mode"] = m.group(1) if m else "unknown"
    facts["products"] = re.findall(r"^### Product:\s*(.+?)\s*$", text, re.M)
    facts["teams"] = re.findall(r"^### Team:\s*(.+?)\s*$", text, re.M)
    # deferred steps: indented bullets right after the marker line
    deferred = []
    m = re.search(r"^- \*\*Deferred steps:\*\*\s*\n((?:\s+- .+\n?)*)", text, re.M)
    if m:
        deferred = re.findall(r"^\s+- (\S+)", m.group(1), re.M)
    facts["deferred_steps"] = deferred
    vault = re.search(r"^## Obsidian Vaults", text, re.M) and re.search(r"^\s*-\s*path:\s*\S+", text, re.M)
    facts["vault_section"] = bool(vault)
    facts["cjm_section"] = bool(re.search(r"^## CJM Configuration\s*\n(?:.*\n){1,6}?.*(?:stages|funnel|template)", text, re.M | re.I))
    facts["terminology_section"] = bool(re.search(r"^### Terminology & Style", text, re.M))
    return facts


def digest(path, facts, searched, version):
    lines = [
        "GROW_PM_SESSION (SessionStart hook, plugin v%s)" % version,
        "local-context.md: FOUND at %s" % path,
        "  configurator version: %s | updated: %s | onboarding mode: %s | user.language: %s"
        % (facts["configurator_version"], facts["updated"], facts["onboarding_mode"], facts["language"]),
    ]
    if facts["products"]:
        lines.append("  products (%d): %s" % (len(facts["products"]), "; ".join(facts["products"][:8])))
    else:
        lines.append("  products: none declared")
    if facts["teams"]:
        lines.append("  teams: %s" % "; ".join(facts["teams"][:6]))
    flags = []
    flags.append("vault: configured" if facts["vault_section"] else "vault: not configured (L0)")
    flags.append("cjm: configured" if facts["cjm_section"] else "cjm: not configured")
    flags.append("team language: configured" if facts["terminology_section"] else "team language: not configured")
    lines.append("  " + " | ".join(flags))
    if facts["deferred_steps"]:
        lines.append("  deferred onboarding steps: %s" % ", ".join(facts["deferred_steps"][:10]))
    lines.append(
        "Skills: take this path for Step 0a of references/local-context-protocol.md and skip the "
        "location search; still parse the file for 0c–0h (product selection, required fields, vault "
        "level). Env GROW_PM_CONTEXT_PATH is set for Bash."
    )
    return "\n".join(lines[:MAX_LINES])


def not_found(searched, version):
    shown = [p for p in searched if "*" not in p][:6]
    return "\n".join([
        "GROW_PM_SESSION (SessionStart hook, plugin v%s)" % version,
        "local-context.md: NOT VISIBLE from this environment (searched %d locations, e.g. %s)."
        % (len(searched), ", ".join(shown)),
        "Skills follow references/local-context-protocol.md Step 0 unchanged (device/file tools, or "
        "the user connects the ~/.grow-pm folder). Do not start onboarding on this signal alone.",
    ])


def export_env(path):
    env_file = os.environ.get("CLAUDE_ENV_FILE")
    if not env_file:
        return
    try:
        with open(env_file, "a", encoding="utf-8") as f:
            f.write("export GROW_PM_CONTEXT_PATH=%s\n" % json.dumps(path))
    except Exception:
        pass


def main():
    data = read_stdin()
    cwd = data.get("cwd") or os.getcwd()
    version = plugin_version()
    searched = candidates(cwd)
    existing = [p for p in searched if os.path.isfile(p)]
    # Rank: the canonical store (~/.grow-pm) first, then any path with a grow-pm
    # segment (a connected copy of the store), then plain copies — a workspace
    # folder may hold a stale export next to design docs.
    def rank(p):
        low = p.lower()
        if low.startswith(os.path.expanduser("~").lower() + os.sep + ".grow-pm"): return 0
        if "/.grow-pm/" in low or "/grow-pm/" in low: return 1
        return 2
    existing.sort(key=rank)
    found = existing[0] if existing else None
    if found:
        try:
            facts = parse(found)
            text = digest(found, facts, searched, version)
            if len(existing) > 1:
                text += "\nOther copies seen (not used; check they are not stale): " + "; ".join(existing[1:4])
        except Exception:
            text = "GROW_PM_SESSION (plugin v%s)\nlocal-context.md: FOUND at %s (digest unavailable — parse error; skills read it themselves)." % (version, found)
        export_env(found)
    else:
        text = not_found(searched, version)
    print(json.dumps({"hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": text}}))


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass
    sys.exit(0)
