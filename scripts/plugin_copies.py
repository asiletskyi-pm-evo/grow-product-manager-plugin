#!/usr/bin/env python3
"""The copies of a plugin installed on this machine (since v4.12.1).

One list of the places a host keeps its copy, read by the two things that ask «which version
is where»: the SessionStart digest's `plugin copies:` line (scripts/session_start.py) and the
reach check of a release (testing/release_reach.py). A copy is found by the plugin's `name`
in its manifest, never by a folder's name. File reads only: no network, nothing written.

Where each host keeps its copy and how soon it updates: references/host-profiles.md §8.
stdlib only.
"""
import glob
import json
import os
import re

MANIFEST = ".claude-plugin/plugin.json"
VERSION_RE = re.compile(r"\d+(?:\.\d+){0,3}(?:[-+][0-9A-Za-z.+-]{0,24})?\Z")   # 4.12.1, 4.13.0-rc1 — never a sentence

# (host, folder under the home, folder levels below it, manifest, how many of those levels are names worth showing).
# The levels not shown are account, organisation and plugin ids: `shown` prints them as `*`.
PLACES = (
    ("Claude desktop app", ("Library", "Application Support", "Claude", "local-agent-mode-sessions"),
     ("*", "*", "rpm", "*"), MANIFEST, 0),
    ("Claude Code (synced from claude.ai)", (".claude", "plugins", "synced"), ("*", "*"), MANIFEST, 1),
    ("Codex", (".codex", "plugins", "cache"), ("*", "*", "*"), ".codex-plugin/plugin.json", 2),
)
INSTALL_RECORD = (".claude", "plugins", "installed_plugins.json")
SYNCED = PLACES[1][0]            # the one place whose folders have a record of which is live
SYNC_MANIFEST = "manifest.json"  # beside the plugin folders: {"plugins": [{"name", "generation"?}, …]}


def read_manifest(path):
    """(name, version) of a plugin manifest, or (None, None) when it is unreadable."""
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        return data.get("name"), data.get("version")
    except (OSError, ValueError, AttributeError):
        return None, None


def version_key(v):
    """The numbers a version starts with, as a tuple — (4, 13, 0) for `4.13.0-rc1`; None when it starts with none."""
    m = re.match(r"\d+(?:\.\d+)*", str(v))
    return tuple(int(x) for x in m.group(0).split(".")) if m else None


def compare(found, expected):
    """ok | behind | ahead for a copy's version against the expected one. With the same numbers, a version with a
    suffix (a pre-release) is behind the one without."""
    if found == expected:
        return "ok"
    a, b = version_key(found), version_key(expected)
    if a is None or b is None:
        return "behind"
    if a == b:
        return "ahead" if len(str(found)) < len(str(expected)) else "behind"
    return "ahead" if a > b else "behind"


def _name(text):
    """A folder's name as one safe word: it is shown to a model, so nothing but name characters."""
    return re.sub(r"[^\w.~+@-]", "?", str(text))[:64]


def shown(base, root, levels, keep):
    """`~/<the place>/*/…/<the last `keep` folder names>` — a copy's folder with its ids as `*`."""
    names = root.split(os.sep)[-len(levels):]
    first_kept = len(levels) - keep
    tail = [lvl if lvl != "*" else ("*" if i < first_kept else _name(names[i])) for i, lvl in enumerate(levels)]
    return "/".join(["~", *base, *tail])


def live_synced_folder(account_dir, name):
    """The folder name the account sync loads the plugin `name` from — `<name>~g<N>` when its record names a
    generation N, `<name>` when it names none — or None when the record is absent, unreadable or does not list the
    plugin. A sync into a new generation writes a new folder and leaves the old ones beside it
    (references/host-profiles.md §8)."""
    try:
        with open(os.path.join(account_dir, SYNC_MANIFEST), encoding="utf-8") as f:
            plugins = json.load(f).get("plugins")
        for p in plugins if isinstance(plugins, list) else []:
            if isinstance(p, dict) and p.get("name") == name:
                g = p.get("generation")
                return "%s~g%d" % (name, g) if isinstance(g, int) and not isinstance(g, bool) else name
    except (OSError, ValueError, AttributeError):
        pass
    return None


def installed_copies(home, name):
    """[(host, version, folder, folder shown without ids, live)] for every copy of the plugin `name` under `home`.
    A manifest that cannot be read, another plugin's, or one whose version is not a version is left out. `live` is
    False for a folder an earlier account sync left behind: the sync's own record names another folder as the one
    loaded. Every other copy is live."""
    found, live_in = [], {}
    for where, base, levels, manifest, keep in PLACES:
        pattern = os.path.join(home, *base, *levels, manifest)
        for path in sorted(glob.glob(pattern)):
            n, v = read_manifest(path)
            if n != name or not isinstance(v, str) or not VERSION_RE.match(v):
                continue
            root = os.path.dirname(os.path.dirname(path))
            live = True
            if where == SYNCED:
                account = os.path.dirname(root)
                if account not in live_in:
                    live_in[account] = live_synced_folder(account, name)
                live = live_in[account] in (None, os.path.basename(root))
            found.append((where, v, root, shown(base, root, levels, keep), live))
    try:
        with open(os.path.join(home, *INSTALL_RECORD), encoding="utf-8") as f:
            plugins = json.load(f).get("plugins", {})
        for key, entries in plugins.items():
            if key.split("@")[0] != name or not isinstance(entries, list):
                continue
            for e in entries:
                v = e.get("version") if isinstance(e, dict) else None
                if isinstance(v, str) and VERSION_RE.match(v):
                    path = e.get("installPath") if isinstance(e.get("installPath"), str) else key
                    found.append(("Claude Code (marketplace install)", v, path, _name(key), True))
    except (OSError, ValueError, AttributeError):
        pass
    return found
