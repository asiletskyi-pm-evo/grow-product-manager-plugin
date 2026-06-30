#!/usr/bin/env python3
"""Static lint (Stage 1) for the Grow PM plugin.
Usage: python3 skill_lint.py [PLUGIN_ROOT]   (default: cwd)
FAIL = release blocker; WARN = take note (external reference in a partial package / dangling ref in a body)."""
import os, re, sys, glob

root = sys.argv[1] if len(sys.argv) > 1 else "."
fails, warns = [], []
IGNORE_MD = {"local-context.md", "local-context.example.md", "SKILL.md", "README.md",
             "CHANGELOG.md", "library.md", "sources.md", "_registry.json"}

def fm(text):
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n", text, re.S)
    return m.group(1) if m else None

def field(block, key):
    m = re.search(rf"^{key}:\s*(.+?)\s*$", block, re.M)
    return m.group(1).strip().strip('"').strip("'") if m else None

# existing reference files (root + per-skill)
refs = set()
ref_paths = glob.glob(os.path.join(root, "references", "*.md")) + \
            glob.glob(os.path.join(root, "skills", "*", "references", "*.md"))
for p in ref_paths:
    refs.add(os.path.basename(p))

skill_files = sorted(glob.glob(os.path.join(root, "skills", "*", "SKILL.md")))
if not skill_files:
    print(f"[!] No skills/*/SKILL.md found in {root}"); sys.exit(2)

semver = re.compile(r"^\d+\.\d+\.\d+$")
for sf in skill_files:
    folder = os.path.basename(os.path.dirname(sf))
    text = open(sf, encoding="utf-8").read()
    block = fm(text); tag = folder
    if not block:
        fails.append(f"{tag}: no YAML frontmatter"); continue
    name = field(block, "name"); ver = field(block, "version"); desc = field(block, "description")
    if not name: fails.append(f"{tag}: no name")
    elif name != folder: fails.append(f"{tag}: name '{name}' != folder '{folder}'")
    if not ver: fails.append(f"{tag}: no version")
    elif not semver.match(ver): fails.append(f"{tag}: version '{ver}' is not semver")
    if not desc: fails.append(f"{tag}: no description")
    elif len(desc) < 40: warns.append(f"{tag}: description is short (<40 chars)")
    for m in re.finditer(r'skill_version:\s*["\']?([\d.]+)', text):
        if ver and m.group(1) != ver:
            fails.append(f"{tag}: skill_version in body '{m.group(1)}' != frontmatter '{ver}'")
    for m in set(re.findall(r"references/([\w-]+\.md)", text)):
        if m not in refs:
            warns.append(f"{tag}: reference '{m}' not found in package (check in the full repo)")

# v1.16: dangling refs in the BODIES of reference files (backticked *.md)
for rp in ref_paths:
    t = open(rp, encoding="utf-8").read()
    for m in set(re.findall(r"`([\w-]+\.md)`", t)):
        if re.search(r"\d{4}-\d{2}-\d{2}", m):   # artifact example (dated name) — not a reference
            continue
        if m not in refs and m not in IGNORE_MD:
            warns.append(f"{os.path.basename(rp)}: backticked '{m}' does not resolve as a reference")

print(f"== Static lint: {root} ==")
print(f"skills: {len(skill_files)} | reference files: {len(refs)}")
print(f"\nFAIL: {len(fails)}")
for f in fails: print("  ✗", f)
print(f"\nWARN: {len(warns)}")
for w in warns: print("  •", w)
print("\nRESULT:", "GREEN ✅" if not fails else "RED ❌ (blockers present)")
sys.exit(1 if fails else 0)
