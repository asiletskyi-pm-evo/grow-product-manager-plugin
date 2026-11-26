#!/usr/bin/env python3
"""TC-release-reach — testing/release_reach.py.

A release is finished when it has reached every place that serves it, not when the tag
exists. The script compares the canonical remote's branch and tag with each mirror and
with the copies of the plugin installed on this machine, and exits 1 while anything is
behind or could not be checked. Built on throw-away git repositories (bare remotes on
disk) and a fictional home folder with a fictional plugin; stdlib + git only.
"""
import json, os, subprocess, sys, tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REACH = os.path.join(ROOT, "testing", "release_reach.py")
NAME = "demo-plugin"
fails = 0
def check(name, cond, detail=""):
    global fails
    fails += not cond
    print(("✅" if cond else "❌"), name, ("" if cond else "-> " + str(detail)[:600]))

ENV = dict(os.environ, GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@example.com",
           GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@example.com")
def git(cwd, *a):
    p = subprocess.run(["git", *a], cwd=cwd, capture_output=True, text=True, env=ENV)
    assert p.returncode == 0, (a, p.stderr)
    return p.stdout.strip()

def manifest(folder, version, name=NAME, sub=".claude-plugin"):
    os.makedirs(os.path.join(folder, sub), exist_ok=True)
    with open(os.path.join(folder, sub, "plugin.json"), "w") as f:
        json.dump({"name": name, "version": version}, f)

def release(work, version):
    """A release as the canonical remote sees it: the bump on main, pushed, and its tag."""
    manifest(work, version)
    git(work, "add", "."); git(work, "commit", "-q", "-m", "release: v" + version)
    git(work, "push", "-q", "origin", "main")
    git(work, "tag", "v" + version); git(work, "push", "-q", "origin", "v" + version)

def reach(work, home, *args):
    p = subprocess.run([sys.executable, REACH, "--repo", work, "--home", home, *args],
                       capture_output=True, text=True, env=ENV)
    return p.returncode, p.stdout, p.stderr

def row(out, where):
    """The status word of the row that names `where` ('' when there is no such row)."""
    for line in out.splitlines():
        if where in line:
            return line.split()[0]
    return ""

with tempfile.TemporaryDirectory() as d:
    origin, mirror, work, home = (os.path.join(d, n) for n in ("origin.git", "mirror.git", "work", "home"))
    for bare in (origin, mirror):
        git(d, "init", "-q", "--bare", "-b", "main", bare)
    git(d, "init", "-q", "-b", "main", work); os.makedirs(home)
    git(work, "remote", "add", "origin", origin)
    release(work, "1.2.0")

    # --- the canonical remote alone -------------------------------------------------
    rc, out, err = reach(work, home)
    check("a release with its tag, no mirror and no installed copy is current", rc == 0 and row(out, "tag v1.2.0") == "ok", (rc, out, err))
    check("the report names the plugin and the version it compares against", NAME in out and "1.2.0" in out, out)
    check("no mirror in this clone is said in one line, not passed over in silence", "no mirror" in out.lower(), out)

    # --- a mirror -------------------------------------------------------------------
    git(work, "remote", "add", "gitlab", mirror)
    rc, out, err = reach(work, home)
    check("a mirror that never got the release is behind and fails the run", rc == 1 and row(out, "gitlab") == "behind", (rc, out, err))
    git(work, "push", "-q", "gitlab", "main")
    rc, out, err = reach(work, home)
    check("a mirror with the branch but without the tag is still behind, and the tag is named",
          rc == 1 and row(out, "gitlab") == "behind" and "v1.2.0" in [l for l in out.splitlines() if "gitlab" in l][0], (rc, out))
    git(work, "push", "-q", "gitlab", "v1.2.0")
    rc, out, err = reach(work, home)
    check("a mirror with the branch and the tag is current", rc == 0 and row(out, "gitlab") == "ok", (rc, out, err))

    git(work, "remote", "add", "mirror", mirror)   # a second name for the same address
    rc, out, err = reach(work, home)
    check("two remote names for one address are one row that names both",
          rc == 0 and sum(l.split()[1:2] == ["mirror"] for l in out.splitlines()) == 1 and "also" in out, out)
    git(work, "remote", "remove", "mirror")

    rc, out, err = reach(work, home, "--mirror", "registry")
    check("a mirror named on the command line but not configured here is not checked, and that fails the run",
          rc == 1 and row(out, "registry") == "unchecked", (rc, out, err))

    git(work, "remote", "add", "vpn", os.path.join(d, "no-such-remote.git"))
    rc, out, err = reach(work, home)
    check("a mirror that cannot be reached is unchecked — one line, exit 1, no traceback",
          rc == 1 and row(out, "vpn") == "unchecked" and "Traceback" not in err, (rc, out, err[-300:]))
    git(work, "remote", "remove", "vpn")

    # --- merged, not released -------------------------------------------------------
    manifest(work, "1.3.0"); git(work, "add", "."); git(work, "commit", "-q", "-m", "release: v1.3.0")
    git(work, "push", "-q", "origin", "main")
    rc, out, err = reach(work, home)
    check("a version on the canonical branch without its tag is behind (merged is not released)",
          rc == 1 and row(out, "tag v1.3.0") == "behind", (rc, out, err))
    check("the mirror is then behind the canonical branch too", row(out, "gitlab") == "behind", out)
    git(work, "tag", "v1.3.0"); git(work, "push", "-q", "origin", "v1.3.0"); git(work, "push", "-q", "gitlab", "main", "v1.3.0")
    rc, out, err = reach(work, home)
    check("after the tag and the mirror push the release is current again", rc == 0, (rc, out, err))

    git(work, "push", "-q", "-f", "gitlab", "HEAD~1:refs/tags/v1.3.0")   # the mirror's tag on another commit
    rc, out, err = reach(work, home)
    check("a mirror whose tag points at another commit than the canonical tag is behind",
          rc == 1 and row(out, "gitlab") == "behind" and "another commit" in out, (rc, out, err))
    git(work, "push", "-q", "-f", "gitlab", "v1.3.0")
    rc, out, err = reach(work, home, "--mirror", "origin")
    check("the canonical remote named as a mirror is not a second row", rc == 0 and "mirror origin" not in out, (rc, out, err))

    # --- the copies installed on this machine -----------------------------------------
    app = os.path.join(home, "Library", "Application Support", "Claude", "local-agent-mode-sessions", "u1", "o1", "rpm")
    synced = os.path.join(home, ".claude", "plugins", "synced", "o1_u1")
    codex = os.path.join(home, ".codex", "plugins", "cache", "demo-market", NAME)
    manifest(os.path.join(app, "plugin_01abc"), "1.3.0")
    manifest(os.path.join(app, "plugin_02xyz"), "0.1.0", name="someone-elses-plugin")
    rc, out, err = reach(work, home)
    check("the desktop app's copy at the released version is current; another plugin's copy is not reported",
          rc == 0 and row(out, "Claude desktop app") == "ok" and "someone-elses-plugin" not in out and "0.1.0" not in out, (rc, out, err))

    manifest(os.path.join(synced, NAME + "~g5"), "1.2.0")
    rc, out, err = reach(work, home)
    check("an older copy synced into Claude Code is behind, with its version and its folder",
          rc == 1 and row(out, "Claude Code") == "behind" and "1.2.0" in out and NAME + "~g5" in out, (rc, out, err))
    rc2, out2, _ = reach(work, home, "--skip-hosts")
    check("--skip-hosts leaves the installed copies out (right after a release they have not synced yet)",
          rc2 == 0 and "Claude" not in out2, (rc2, out2))
    manifest(os.path.join(synced, NAME + "~g5"), "1.3.0")

    manifest(os.path.join(codex, "1.2.0"), "1.2.0", sub=".codex-plugin")
    rc, out, err = reach(work, home)
    check("an older copy in the Codex cache is behind", rc == 1 and row(out, "Codex") == "behind", (rc, out, err))
    manifest(os.path.join(codex, "1.2.0"), "1.3.0", sub=".codex-plugin")

    with open(os.path.join(home, ".claude", "plugins", "installed_plugins.json"), "w") as f:
        json.dump({"version": 2, "plugins": {NAME + "@demo-market": [{"version": "1.1.0", "installPath": "/x"}],
                                             "other@demo-market": [{"version": "0.0.1"}]}}, f)
    rc, out, err = reach(work, home)
    check("an older marketplace install recorded by Claude Code is behind, and another plugin's record is ignored",
          rc == 1 and "1.1.0" in out and "0.0.1" not in out and row(out, "marketplace install") == "behind", (rc, out, err))
    with open(os.path.join(home, ".claude", "plugins", "installed_plugins.json"), "w") as f:
        f.write("{ not json")
    rc, out, err = reach(work, home)
    check("an unreadable install record is skipped, not a crash", rc == 0 and "Traceback" not in err, (rc, out, err[-300:]))

    manifest(os.path.join(synced, NAME), "9.0.0")
    rc, out, err = reach(work, home)
    check("a copy newer than the release (a development install) is ahead and does not fail the run",
          rc == 0 and "ahead" in out, (rc, out, err))

    manifest(os.path.join(synced, NAME), "9.0.0-rc1")
    rc, out, err = reach(work, home)
    check("…and so is a newer pre-release (9.0.0-rc1)", rc == 0 and "ahead" in out and "9.0.0-rc1" in out, (rc, out, err))

    # --- an explicit version and a broken canonical -----------------------------------
    rc, out, err = reach(work, home, "--version", "v1.2.0", "--skip-hosts")
    check("--version takes the release with or without its leading v", rc == 0 and row(out, "tag v1.2.0") == "ok", (rc, out, err))
    rc, out, err = reach(work, home, "--version", "1.2.0", "--skip-hosts")
    check("--version checks that release's tag rather than the newest one", rc == 0 and row(out, "tag v1.2.0") == "ok", (rc, out, err))
    rc, out, err = reach(work, home, "--canonical", "nowhere")
    check("an unknown canonical remote is one line and exit 1, not a traceback",
          rc == 1 and "nowhere" in out and "Traceback" not in err, (rc, out, err[-300:]))

    # --- a clone that has not fetched the release -------------------------------------
    stale, home2 = os.path.join(d, "stale"), os.path.join(d, "home2"); os.makedirs(home2)
    git(d, "clone", "-q", origin, stale)
    other = os.path.join(d, "other"); git(d, "clone", "-q", origin, other)
    release(other, "1.4.0")
    rc, out, err = reach(stale, home2)
    check("a clone without the canonical branch's newest commit says so and fails, instead of comparing against its own old version",
          rc == 1 and row(out, "this clone") == "behind" and "fetch" in out, (rc, out, err))
    git(stale, "fetch", "-q", "origin", "--tags")
    rc, out, err = reach(stale, home2)
    check("after a fetch the same clone compares against the canonical version, whatever its own branch holds",
          rc == 0 and "1.4.0" in out and row(out, "tag v1.4.0") == "ok", (rc, out, err))

    # --- the folders an earlier sync left behind ----------------------------------------------
    home3 = os.path.join(d, "home3"); acct = os.path.join(home3, ".claude", "plugins", "synced", "o1_u1"); os.makedirs(acct)
    manifest(os.path.join(acct, NAME), "0.5.0"); manifest(os.path.join(acct, NAME + "~g5"), "1.2.0")
    manifest(os.path.join(acct, NAME + "~g2"), "1.4.0")
    def sync_manifest(entry):
        with open(os.path.join(acct, "manifest.json"), "w") as f:
            json.dump({"lastUpdated": "2026-01-01T00:00:00Z", "plugins": [entry, {"name": "other", "generation": 5}]}, f)
    sync_manifest({"name": NAME, "generation": 2})
    rc, out, err = reach(stale, home3)
    lines = [l for l in out.splitlines() if "Claude Code" in l]
    check("the folder the sync manifest names (generation 2 → ~g2) is the copy; older folders beside it are leftovers that do not fail the run",
          rc == 0 and len(lines) == 3 and [l.split()[0] for l in lines].count("leftover") == 2
          and row(out, NAME + "~g2") == "ok" and row(out, NAME + "~g5") == "leftover", (rc, out, err))
    sync_manifest({"name": NAME})
    rc, out, err = reach(stale, home3)
    check("with no generation in the sync manifest the plain folder is the copy — here an old one, so the run fails",
          rc == 1 and row(out, "0.5.0") == "behind" and row(out, NAME + "~g2") == "leftover", (rc, out, err))
    with open(os.path.join(acct, "manifest.json"), "w") as f:
        f.write("{ not json")
    rc, out, err = reach(stale, home3)
    check("an unreadable sync manifest leaves every folder a copy, as before", rc == 1 and "leftover" not in out and "Traceback" not in err, (rc, out, err[-300:]))

    # --- a manifest that is not a manifest -------------------------------------------------
    odd_origin, odd = os.path.join(d, "odd.git"), os.path.join(d, "odd")
    git(d, "init", "-q", "--bare", "-b", "main", odd_origin); git(d, "init", "-q", "-b", "main", odd)
    git(odd, "remote", "add", "origin", odd_origin)
    os.makedirs(os.path.join(odd, ".claude-plugin"))
    with open(os.path.join(odd, ".claude-plugin", "plugin.json"), "w") as f:
        f.write("[1, 2]")
    git(odd, "add", "."); git(odd, "commit", "-q", "-m", "odd"); git(odd, "push", "-q", "origin", "main")
    rc, out, err = reach(odd, home2)
    check("a manifest that is not an object is one line and exit 1, not a traceback",
          rc == 1 and "unchecked" in out and "Traceback" not in err, (rc, out, err[-300:]))
    git(odd, "tag", "v1.0.0"); git(odd, "push", "-q", "origin", "v1.0.0")
    rc, out, err = reach(odd, home2, "--version", "1.0.0")
    check("with no plugin name the installed copies are said to be unchecked, never passed in silence",
          rc == 1 and row(out, "installed copies") == "unchecked" and "Traceback" not in err, (rc, out, err[-300:]))

print("RESULT:", "GREEN ✅" if not fails else "RED ❌", "(%d failed)" % fails)
sys.exit(1 if fails else 0)
