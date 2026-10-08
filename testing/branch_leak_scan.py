#!/usr/bin/env python3
"""Branch leak scan — no organisation identifier enters the repository through a branch.

The static lint (skill_lint.py, checks 9 and 16-18) scans the prose that ships; it does
not read CHANGELOG.md, docs/ or commit messages, and a design note pasted into
docs/ is exactly where an organisation's names arrive. This scan reads every line the
branch ADDS against its base (all files, any type) and every commit message on the
branch, and fails on any token of the gitignored denylist `testing/org-tokens.local`
(the same file and the same word-boundary rule as lint check 9).

  python3 testing/branch_leak_scan.py [--base main] [--tokens testing/org-tokens.local]

Exit 0 — clean, or no denylist on this machine (a notice is printed: the scan cannot
run without it). Exit 1 — hits, one line each. Exit 2 — the base ref is not in this
clone (a shallow clone, or the branch was never fetched); one line, never a pass.
Run it before every push of a branch (release-manager Step 1). Stdlib + git only.
"""
import argparse, os, re, subprocess, sys


def tokens_rx(path):
    if not os.path.isfile(path):
        return None
    toks = [l.strip() for l in open(path, encoding="utf-8") if l.strip() and not l.startswith("#")]
    if not toks:
        return None
    bound = lambda t: (r"\b" if t[:1].isalnum() else "") + re.escape(t) + (r"\b" if t[-1:].isalnum() else "")
    return re.compile("|".join(bound(t) for t in toks), re.I)


def git(*args):
    return subprocess.run(["git", *args], capture_output=True, text=True, check=True).stdout


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="main")
    ap.add_argument("--tokens", default=os.path.join("testing", "org-tokens.local"))
    a = ap.parse_args()
    rx = tokens_rx(a.tokens)
    if rx is None:
        print("branch-leak-scan: no denylist at %s — scan skipped (copy org-tokens.local.example)" % a.tokens)
        return 0
    if subprocess.run(["git", "rev-parse", "--verify", "--quiet", a.base + "^{commit}"], capture_output=True).returncode:
        print("branch-leak-scan: base '%s' is not in this clone — fetch it (git fetch origin %s) or pass --base <ref>; "
              "nothing was scanned" % (a.base, a.base))
        return 2
    hits = []
    cur = None
    for line in git("diff", "--unified=0", "--no-color", "%s...HEAD" % a.base).split("\n"):
        if line.startswith("+++ "):
            cur = line[6:] if line.startswith("+++ b/") else line[4:]
        elif line.startswith("+") and not line.startswith("+++"):
            m = rx.search(line)
            if m:
                hits.append("%s: added line carries '%s'" % (cur, m.group(0)))
    for entry in git("log", "--format=%h%x00%B%x01", "%s..HEAD" % a.base).split("\x01"):
        if "\x00" not in entry:
            continue
        sha, msg = entry.strip("\n").split("\x00", 1)
        m = rx.search(msg)
        if m:
            hits.append("commit %s: message carries '%s'" % (sha, m.group(0)))
    for h in hits:
        print("LEAK", h)
    print("branch-leak-scan: %s" % ("clean" if not hits else "%d hit(s) — rewrite them before pushing" % len(hits)))
    return 1 if hits else 0


if __name__ == "__main__":
    sys.exit(main())
