#!/usr/bin/env python3
"""Seeded-leak test (Stage 1b) for the Grow PM plugin.

A check nobody has watched fail is a promise, not a test. This script proves
that the checks in `skill_lint.py` whose failure mode is silence actually fire:
it copies the repo to a temp dir, applies one known-bad edit at a time (a line
appended, removed or replaced — see SEEDS), and asserts the linter goes RED with
the expected check tag. The org-leak seeds are real defect classes that shipped —
see CHANGELOG v2.4.1 and `Testing-process.md` — rewritten with a fictional org
("Zorg", "ZORG") so no real identifier enters the repository. The role-layer
seeds (checks 19-22, JCRL v3.5.0) and the judgment-points seeds (check 23,
v3.7.0) are preventive: their classes have not shipped.

Usage: python3 testing/seeded_leak_test.py [PLUGIN_ROOT]   (default: repo root)
Exit 0 = every seeded defect was caught; exit 1 = at least one slipped through.
Run it after touching skill_lint.py, and as part of the release DoD.
"""
import os, re, shutil, subprocess, sys, tempfile

root = os.path.abspath(sys.argv[1] if len(sys.argv) > 1
                       else os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

# (name, target file, mode, payload, expected check tag)
#   mode "append"  — payload is a line added at the end of the file (the original
#                    behaviour: a leak is something that gets written in);
#   mode "remove"  — payload is a regex; the first line matching it is deleted
#                    (a required citation that goes missing);
#   mode "replace" — payload is (regex, replacement), applied once (two sources
#                    of truth drifting apart).
# Text seeds keep the fictional-org rule: nothing real enters the repository.
SEEDS = [
    # v2.5.0: agents/ and commands/ are shipped prose too. Without this seed a
    # leak in an agent's system prompt would pass every check green.
    ("component: real Atlassian host inside an agent prompt",
     "agents/artifact-checker.md", "append",
     "Spot-check claims against https://zorg.atlassian.net/wiki when in doubt.",
     "org-data"),
    ("component: authority citation inside a command",
     "commands/status.md", "append",
     "- Report format: per Zorg convention — one table, then one action line.",
     "org-signature"),
    ("authority: per <Org> convention",
     "references/dependency-model.md", "append",
     "- Link direction: per Zorg convention — a Blocks chain plus Relates pairs.",
     "org-signature"),
    ("authority: (<Org> formatting rules)",
     "skills/product-reporter/SKILL.md", "append",
     "- Confluence: `<th>` headers, links to Jira keys (Zorg formatting rules).",
     "org-signature"),
    ("signature: example signed <Org> + quarter",
     "references/capacity-model.md", "append",
     "## 12. Reference example (Zorg Q3 2026, verified by a run)",
     "org-signature"),
    ("signature: example signed quarter + <Org>",
     "references/roadmap-artifacts.md", "append",
     "Sections (validated by a run of Q3 Zorg):",
     "org-signature"),
    ("signature: attributed to the <Org> team",
     "references/capacity-model.md", "append",
     "These coefficients were measured by the Zorg team over three quarters.",
     "org-signature"),
    ("locale: localized sample value in a fenced block",
     "skills/knowledge-library/references/glossary-workflows.md", "append",
     '```yaml\n- term: "картка товару"\n  status: approved\n```',
     "example-locale"),
    ("locale: hardcoded output language",
     "skills/product-reporter/SKILL.md", "append",
     "- Language: Ukrainian by default (`user.language`).",
     "example-locale"),
    ("keys: real issue key in an example",
     "references/roadmap-artifacts.md", "append",
     "Example: pull the epic ZORG-4821 and read its `issuelinks` field.",
     "example-keys"),
    ("keys: real Confluence space in an example",
     "skills/knowledge-library/references/glossary-workflows.md", "append",
     '- `source: "confluence:ZORG/Team-glossary"` — where the term was mined from.',
     "example-keys"),
    # JCRL v3.5.0 role layer — PREVENTIVE seeds: no defect of these classes has
    # shipped. They prove checks 19-22 fire before the first one does.
    ("role: a skill branches on the role name",
     "skills/quarterly-planning/SKILL.md", "append",
     "If role == cpo, use the strategy memo.",
     "role-branching"),
    ("role: a persona prompt with a product-role identity",
     "references/planning-core.md", "append",
     "You are a CPO reviewing this roadmap.",
     "persona-prompt"),
    ("role: a Product-contour skill loses its judgment-footer citation",
     "skills/write-concept/SKILL.md", "remove",
     r"partial/judgment-footer",
     "judgment-footer"),
    ("role: the two role enums drift apart",
     "references/role-profiles.md", "replace",
     (re.escape("`eng_lead` · "), ""),
     "role-enum"),
    # v3.7.0: judgment-points.md §1 is the complete list of P2 / confidence-line steps.
    ("judgment: a §1 row names a skill that never cites judgment-points.md",
     "references/judgment-points.md", "replace",
     (re.escape("| `quarterly-planning` · "), "| `roadmap-architect` · "),
     "judgment-points"),
    ("judgment: a P2 question outside the §1 list",
     "skills/write-concept/SKILL.md", "append",
     "Before the recommendation, ask the P2 question of the judgment protocol.",
     "judgment-points"),
    ("judgment: a P3 confidence line outside the §1 list",
     "skills/cjm-research/SKILL.md", "append",
     "Close the report with `Confidence: likely · most sensitive to: … · would change if: …`.",
     "judgment-points"),
]

# The denylist layer is optional (gitignored), so it gets its own seed: a bare
# org name that no shape-based rule can recognize, caught only when the
# maintainer has listed it in testing/org-tokens.local.
DENYLIST_SEED = ("denylist: bare org name with org-tokens.local present",
                 "references/roadmap-artifacts.md", "append",
                 "The quarterly cadence at Zorgtech starts two weeks before the quarter.",
                 "org-data")


def apply_seed(original, mode, payload):
    """The seeded text, or None when the seed does not apply — a seed that
    changes nothing proves nothing, so it is reported, never counted as caught."""
    if mode == "append":
        return original + "\n" + payload + "\n"
    if mode == "remove":
        lines = original.split("\n")
        for k, line in enumerate(lines):
            if re.search(payload, line):
                return "\n".join(lines[:k] + lines[k + 1:])
        return None
    if mode == "replace":
        pattern, repl = payload
        seeded, n = re.subn(pattern, repl, original, count=1)
        return seeded if n else None
    raise ValueError(f"unknown seed mode '{mode}'")


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
        for name, rel, mode, payload, tag in SEEDS + [DENYLIST_SEED]:
            path = os.path.join(tree, rel)
            original = open(path, encoding="utf-8").read()
            denylist = os.path.join(tree, "testing", "org-tokens.local")
            seeded = apply_seed(original, mode, payload)
            if seeded is None:
                results.append((False, name, tag))
                print(f"  ❌ {name}  → seed did not apply ({mode}: pattern not found in {rel})")
                continue
            try:
                open(path, "w", encoding="utf-8").write(seeded)
                if tag == "org-data":
                    open(denylist, "w", encoding="utf-8").write("# seeded\nZorgtech\n")
                # the marker the FAIL line must point at: the seeded file's basename
                # (every check that has a seed names the offending file in its FAIL line)
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
        print(f"\ncaught {len(results) - len(missed)}/{len(results)} seeded defects")
        print("RESULT:", "GREEN ✅" if not missed else "RED ❌ (a defect class is unguarded)")
        return 1 if missed else 0
    finally:
        shutil.rmtree(tree, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
