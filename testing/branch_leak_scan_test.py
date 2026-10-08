#!/usr/bin/env python3
"""TC-lint-3100-branch-scan — testing/branch_leak_scan.py.

The static lint scans shipped prose; CHANGELOG, docs/ and commit messages are outside
its scope. The branch scan reads every line a branch ADDS (all files) plus its commit
messages and fails on any token of the gitignored org denylist. Built on a throw-away
git repository with a fictional token; stdlib + git only. Run from the repo root.
"""
import os, subprocess, sys, tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCAN = os.path.join(ROOT, "testing", "branch_leak_scan.py")
fails = 0
def check(name, cond, detail=""):
    global fails
    fails += not cond
    print(("✅" if cond else "❌"), name, ("" if cond else "-> " + str(detail)[:400]))

def git(cwd, *a):
    return subprocess.run(["git", *a], cwd=cwd, capture_output=True, text=True,
                          env=dict(os.environ, GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@example.com",
                                   GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@example.com"))

with tempfile.TemporaryDirectory() as d, tempfile.TemporaryDirectory() as aside:
    git(d, "init", "-q", "-b", "main")
    open(os.path.join(d, "README.md"), "w").write("# Demo\nOld Zorgcorp mention shipped long ago.\n")
    git(d, "add", "."); git(d, "commit", "-q", "-m", "init")
    git(d, "checkout", "-q", "-b", "feature")
    # the denylist lives outside the repo, like the gitignored testing/org-tokens.local
    toks = os.path.join(aside, "tokens.local"); open(toks, "w").write("# denylist\nZorgcorp\nzorg-brain\n")
    def scan():
        p = subprocess.run([sys.executable, SCAN, "--base", "main", "--tokens", toks], cwd=d, capture_output=True, text=True)
        return p.returncode, p.stdout
    open(os.path.join(d, "CHANGELOG.md"), "w").write("## v1\n- neutral entry\n")
    git(d, "add", "."); git(d, "commit", "-q", "-m", "docs: neutral")
    rc, out = scan()
    check("clean branch passes (old lines on main are not re-flagged)", rc == 0, out)
    open(os.path.join(d, "CHANGELOG.md"), "a").write("- replaces the zorg-brain companion\n")
    git(d, "add", "."); git(d, "commit", "-q", "-m", "docs: more")
    rc, out = scan()
    check("added line with a token fails and names file and token", rc == 1 and "CHANGELOG.md" in out and "zorg-brain" in out, out)
    git(d, "reset", "-q", "--hard", "HEAD~1")
    git(d, "commit", "-q", "--allow-empty", "-m", "feat: port the Zorgcorp plugin")
    rc, out = scan()
    check("commit message with a token fails", rc == 1 and "commit" in out.lower(), out)
    rc2 = subprocess.run([sys.executable, SCAN, "--base", "main", "--tokens", os.path.join(d, "absent")], cwd=d,
                         capture_output=True, text=True).returncode
    check("absent denylist is a notice, not a failure", rc2 == 0)
    p = subprocess.run([sys.executable, SCAN, "--base", "no-such-base", "--tokens", toks], cwd=d, capture_output=True, text=True)
    check("a missing base is one line and exit 2, not a traceback", p.returncode == 2 and "Traceback" not in p.stderr
          and "no-such-base" in p.stdout, (p.returncode, p.stdout, p.stderr[-200:]))

print("RESULT:", "GREEN ✅" if not fails else "RED ❌", "(%d failed)" % fails)
sys.exit(1 if fails else 0)
