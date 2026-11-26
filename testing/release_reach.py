#!/usr/bin/env python3
"""Where has the release reached? — release-manager Step 7 and Step 8.

A release is finished when every place that serves the plugin has it, not when the tag
exists. This script reads the version on the canonical remote's branch and compares it with:

  - the canonical remote's own tag (a merged bump without its tag is not a release);
  - every mirror remote of this clone: its branch and its tag;
  - the copies of the plugin installed on this machine (Claude desktop app, Claude Code,
    Codex), found by the plugin's name in their manifests.

It writes nothing and changes nothing: `git ls-remote` for the remotes, file reads for the
copies. Exit 0 — everything it could see is current. Exit 1 — something is behind or could
not be checked; the rows say what. An installed copy that is absent is not a failure, and
neither is one newer than the release (a development install), nor a `leftover` — a folder
an earlier account sync left beside the one it loads now.

  python3 testing/release_reach.py                 # after the merge and the mirror push
  python3 testing/release_reach.py --skip-hosts    # remotes only: the hosts have not synced yet
  python3 testing/release_reach.py --mirror gitlab # a mirror this clone must have

Where each host keeps its copy and how soon it updates: references/host-profiles.md §8.
stdlib + git only.
"""
import argparse, json, os, subprocess, sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"))
from plugin_copies import MANIFEST, compare, installed_copies, read_manifest   # one list of places, shared with the SessionStart digest

GIT_TIMEOUT_S = 30


def git(repo, *args):
    """(ok, stdout) of one git command; never prompts for a password and never raises."""
    env = dict(os.environ, GIT_TERMINAL_PROMPT="0")
    try:
        p = subprocess.run(["git", "-C", repo, *args], capture_output=True, text=True,
                           env=env, timeout=GIT_TIMEOUT_S)
    except (OSError, subprocess.TimeoutExpired):
        return False, ""
    return p.returncode == 0, p.stdout


def ls_remote(repo, remote, *refs):
    """{ref: sha} of the refs that exist on the remote, or None when it cannot be reached."""
    ok, out = git(repo, "ls-remote", remote, *refs)
    if not ok:
        return None
    found = {}
    for line in out.splitlines():
        sha, _, ref = line.partition("\t")
        if ref and not ref.endswith("^{}"):
            found[ref] = sha
    return found


def mirrors_of(repo, canonical, named):
    """[(name, other names with the same address)] — every remote but the canonical one,
    one row per address; a name asked for with --mirror that is not a remote here keeps
    its row so the run can say it was not checked."""
    ok, out = git(repo, "remote")
    remotes = [r for r in out.split() if r != canonical] if ok else []
    by_url, order = {}, []
    for r in remotes:
        ok, url = git(repo, "remote", "get-url", r)
        url = url.strip() if ok else r
        if url in by_url:
            by_url[url].append(r)
        else:
            by_url[url] = [r]; order.append(url)
    rows = [(by_url[u][0], by_url[u][1:], True) for u in order]
    for n in named:
        if n not in remotes and n != canonical:
            rows.append((n, [], False))
    return rows


def main():
    ap = argparse.ArgumentParser(description="Where has the release reached?")
    ap.add_argument("--repo", default=os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    ap.add_argument("--canonical", default="origin", help="the remote releases are merged on")
    ap.add_argument("--branch", default="main")
    ap.add_argument("--mirror", action="append", default=[], help="a mirror remote that must be checked (repeatable)")
    ap.add_argument("--version", help="check this release instead of the one on the canonical branch")
    ap.add_argument("--home", default=os.path.expanduser("~"), help="where the installed copies are looked for")
    ap.add_argument("--skip-hosts", action="store_true", help="remotes only")
    a = ap.parse_args()

    rows = []   # (status, where, detail)
    head_ref = "refs/heads/" + a.branch
    canon = ls_remote(a.repo, a.canonical, head_ref)
    if not canon or head_ref not in canon:
        print("unchecked   %s  cannot read %s from the remote '%s' — is it configured and reachable?"
              % (a.canonical, a.branch, a.canonical))
        print("\nrelease reach: nothing could be compared")
        return 1
    head = canon[head_ref]

    # The version is the one on the canonical branch; this clone can read it only once fetched.
    name, tree_version = read_manifest(os.path.join(a.repo, MANIFEST))
    version = a.version[1:] if a.version and a.version.startswith("v") else a.version
    ok, _ = git(a.repo, "cat-file", "-e", head + "^{commit}")
    if ok:
        shown, text = git(a.repo, "show", "%s:%s" % (head, MANIFEST))
        try:
            data = json.loads(text) if shown else {}
        except ValueError:
            data = {}
        if not isinstance(data, dict):
            data = {}
        name, version = data.get("name") or name, version or data.get("version") or tree_version
        rows.append(("ok", "this clone", "has %s/%s %s" % (a.canonical, a.branch, head[:7])))
    else:
        version = version or tree_version
        rows.append(("behind", "this clone", "does not have %s/%s %s — git fetch %s, then run again"
                     % (a.canonical, a.branch, head[:7], a.canonical)))
    if not version:
        print("unchecked   this clone  no version in %s" % MANIFEST)
        return 1
    tag_ref = "refs/tags/v" + version

    tags, canon_tag = ls_remote(a.repo, a.canonical, tag_ref), None
    if tags is None:
        rows.append(("unchecked", a.canonical, "tag v%s — the remote stopped answering" % version))
    elif tag_ref in tags:
        canon_tag = tags[tag_ref]
        rows.append(("ok", a.canonical, "tag v%s" % version))
    else:
        rows.append(("behind", a.canonical, "tag v%s is missing — merged is not released" % version))

    mirrors = mirrors_of(a.repo, a.canonical, a.mirror)
    for mname, also, configured in mirrors:
        where = "mirror " + mname
        suffix = " (also: %s)" % ", ".join(also) if also else ""
        if not configured:
            rows.append(("unchecked", where, "not a remote of this clone — check it from the machine that has it"))
            continue
        refs = ls_remote(a.repo, mname, head_ref, tag_ref)
        if refs is None:
            rows.append(("unchecked", where, "cannot be reached from here (VPN?)" + suffix))
            continue
        lacks = []
        if refs.get(head_ref) != head:
            lacks.append("%s is not at %s" % (a.branch, head[:7]))
        if tag_ref not in refs:
            lacks.append("tag v%s is missing" % version)
        elif canon_tag and refs[tag_ref] != canon_tag:
            lacks.append("tag v%s points at another commit than on %s" % (version, a.canonical))
        if lacks:
            rows.append(("behind", where, "; ".join(lacks) + suffix))
        else:
            rows.append(("ok", where, "%s %s, tag v%s%s" % (a.branch, head[:7], version, suffix)))

    if not a.skip_hosts and not name:
        rows.append(("unchecked", "installed copies", "no plugin name in %s — the copies on this machine were not looked for" % MANIFEST))
    elif not a.skip_hosts:
        home = a.home.rstrip(os.sep)
        for where, v, path, _, live in installed_copies(a.home, name):
            shown_path = "~" + path[len(home):] if path == home or path.startswith(home + os.sep) else path
            if live:
                rows.append((compare(v, version), where, "%s  %s" % (v, shown_path)))
            else:                                   # the sync's record names another folder as the one loaded
                rows.append(("leftover", where, "%s  %s — not loaded, an earlier sync left it" % (v, shown_path)))

    print("release reach — %s v%s (%s/%s %s)\n" % (name, version, a.canonical, a.branch, head[:7]))
    width = max(len(w) for _, w, _ in rows)
    for status, where, detail in rows:
        print("%-10s  %-*s  %s" % (status, width, where, detail))
    if not mirrors:
        print("note        no mirror remote in this clone — a mirror kept elsewhere is not checked by this run")
    behind = sum(s == "behind" for s, _, _ in rows)
    unchecked = sum(s == "unchecked" for s, _, _ in rows)
    print("\n%d behind, %d not checked" % (behind, unchecked))
    return 1 if behind or unchecked else 0


if __name__ == "__main__":
    sys.exit(main())
