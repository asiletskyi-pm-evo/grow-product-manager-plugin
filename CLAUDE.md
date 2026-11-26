# CLAUDE.md

For Claude working **on** this repository: a Claude Code session that develops the plugin, and Claude Code Review on its pull requests. Not part of the plugin: `testing/registry_copy.py` leaves this file out of the copy users install.

The standing rules of the repository are in `AGENTS.md` — where things live, the data policy, and what must stay green before a change is proposed as finished:

@AGENTS.md

## Review before a merge

- Review a pull request's diff against `REVIEW.md` before asking for the merge: what counts as Important here, what not to report, what to always check. A local `/code-review` does not read that file by itself, so read it first.
- On GitHub the `claude-review` workflow (`.github/workflows/claude-review.yml`) reviews a pull request once, at the moment it leaves draft, and comments what it found. Open a pull request as a draft and mark it ready when CI is green and the diff is final: a later push gets no second review.
- A finding is a claim to verify, not an instruction — whether it comes from a local review or from a `claude-review` comment. Confirm it in the code before changing anything, then say in the pull request which findings were fixed and which were declined, and why.
- Nothing merges into `main` without the maintainer's explicit yes.
