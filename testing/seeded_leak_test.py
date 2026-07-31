#!/usr/bin/env python3
"""Seeded-leak test (Stage 1b) for the Grow PM plugin.

A check nobody has watched fail is a promise, not a test. This script proves
that the org-leak checks in `skill_lint.py` actually fire: it copies the repo to
a temp dir, injects one known-bad line at a time, and asserts the linter goes RED
with the expected check tag. Every seed is a real defect class that shipped —
see CHANGELOG v2.4.1 and `Testing-process.md` — rewritten with a fictional org
("Zorg", "ZORG") so no real identifier enters the repository.

Usage: python3 testing/seeded_leak_test.py [PLUGIN_ROOT]   (default: repo root)
Exit 0 = every seeded leak was caught; exit 1 = at least one slipped through.
Run it after touching skill_lint.py, and as part of the release DoD.
"""
import os, re, shutil, subprocess, sys, tempfile

root = os.path.abspath(sys.argv[1] if len(sys.argv) > 1
                       else os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

# (name, target file, injected text, expected check tag)
SEEDS = [
    ("authority: per <Org> convention",
     "references/dependency-model.md",
     "- Link direction: per Zorg convention — a Blocks chain plus Relates pairs.",
     "org-signature"),
    ("authority: (<Org> formatting rules)",
     "skills/product-reporter/SKILL.md",
     "- Confluence: `<th>` headers, links to Jira keys (Zorg formatting rules).",
     "org-signature"),
    ("signature: example signed <Org> + quarter",
     "references/capacity-model.md",
     "## 12. Reference example (Zorg Q3 2026, verified by a run)",
     "org-signature"),
    ("signature: example signed quarter + <Org>",
     "references/roadmap-artifacts.md",
     "Sections (validated by a run of Q3 Zorg):",
     "org-signature"),
    ("signature: attributed to the <Org> team",
     "references/capacity-model.md",
     "These coefficients were measured by the Zorg team over three quarters.",
     "org-signature"),
    ("locale: localized sample value in a fenced block",
     "skills/knowledge-library/references/glossary-workflows.md",
     '```yaml\n- term: "картка товару"\n  status: approved\n```',
     "example-locale"),
    ("locale: hardcoded output language",
     "skills/product-reporter/SKILL.md",
     "- Language: Ukrainian by default (`user.language`).",
     "example-locale"),
    ("keys: real issue key in an example",
     "references/roadmap-artifacts.md",
     "Example: pull the epic ZORG-4821 and read its `issuelinks` field.",
     "example-keys"),
    ("keys: real Confluence space in an example",
     "skills/knowledge-library/references/glossary-workflows.md",
     '- `source: "confluence:ZORG/Team-glossary"` — where the term was mined from.',
     "example-keys"),
]

# The denylist layer is optional (gitignored), so it gets its own seed: a bare
# org name that no shape-based rule can recognize, caught only when the
# maintainer has listed it in testing/org-tokens.local.
DENYLIST_SEED = ("denylist: bare org name with org-tokens.local present",
                 "references/roadmap-artifacts.md",
                 "The quarterly cadence at Zorgtech starts two weeks before the quarter.",
                 "org-data")


def run_lint(tree):
    p = subprocess.run([sys.executable, os.path.join(tree, "testing", "skill_lint.py"), tree],
                       capture_output=True, text=True)
    return p.returncode, p.stdout + p.stderr


def caught(out, tag, needle):
    """A FAIL line with the right tag that points at the seeded text."""
    for line in out.splitlines():
        if line.strip().startswith("✗") and f"[{tag}]" in line and needle in line:
            return True
    return False


def main():
    tree = tempfile.mkdtemp(prefix="grow-seeded-")
    try:
        shutil.copytree(root, tree, dirs_exist_ok=True,
                        ignore=shutil.ignore_patterns(".git", "__pycache__", "*.pyc"))
        # Baseline: a green tree, so every RED below is caused by the seed alone.
        code, out = run_lint(tree)
        if code != 0:
            print("BASELINE RED — fix the repo before running the seeded test:\n")
            print(out)
            return 1
        print(f"baseline: GREEN ✅   seeds: {len(SEEDS) + 1}\n")

        results = []
        for name, rel, text, tag in SEEDS + [DENYLIST_SEED]:
            path = os.path.join(tree, rel)
            original = open(path, encoding="utf-8").read()
            denylist = os.path.join(tree, "testing", "org-tokens.local")
            try:
                open(path, "a", encoding="utf-8").write("\n" + text + "\n")
                if tag == "org-data":
                    open(denylist, "w", encoding="utf-8").write("# seeded\nZorgtech\n")
                # the marker the FAIL line must point at: the seeded file
                _, out = run_lint(tree)
                ok = caught(out, tag, os.path.basename(rel))
                results.append((ok, name, tag))
                print(f"  {'✅' if ok else '❌'} {name}  → expected [{tag}]")
                if not ok:
                    for line in out.splitlines():
                        if line.strip().startswith("✗"):
                            print(f"       got: {line.strip()}")
            finally:
                open(path, "w", encoding="utf-8").write(original)
                if os.path.isfile(denylist): os.remove(denylist)

        missed = [r for r in results if not r[0]]
        print(f"\ncaught {len(results) - len(missed)}/{len(results)} seeded leaks")
        print("RESULT:", "GREEN ✅" if not missed else "RED ❌ (a leak class is unguarded)")
        return 1 if missed else 0
    finally:
        shutil.rmtree(tree, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
