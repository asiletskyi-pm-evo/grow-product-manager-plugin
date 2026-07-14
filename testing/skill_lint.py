#!/usr/bin/env python3
"""Static lint (Stage 1) for the Grow PM plugin.

Usage: python3 skill_lint.py [PLUGIN_ROOT]   (default: cwd)
FAIL = release blocker; WARN = take note.

Every check below exists because the defect class it catches actually shipped.
The 2026-07-14 audit found 5 critical + 14 major defects that the previous
linter passed green; each is now a named check (see CHECKS below).

Stdlib-only by design (runs in CI without pip install). PyYAML is used for an
extra strict parse when available, but the hazard scan does not depend on it.
"""
import os, re, sys, glob, json

CHECKS = """
 1. frontmatter-yaml     strict YAML validity (plain-scalar hazards: ': ', ' #')
 2. frontmatter-fields   name==folder, semver, description present and <= 1024
 3. skill-version-sync   inline skill_version == frontmatter version
 4. ref-paths            every referenced path resolves (incl. subdirs, .yaml)
 5. ghost-skill          chain targets that are not real skills
 6. stale-names          pre-rename identifiers outside CHANGELOG history
 7. duplicate-h1         a doc containing itself twice
 8. readme-versions      README skill versions == SKILL.md frontmatter
 9. org-data             real org identifiers in shipped example/templates/refs
10. deck-subtypes        deck-subtypes.yaml keys == built-in template subtypes
"""

root = sys.argv[1] if len(sys.argv) > 1 else "."
fails, warns = [], []
def fail(tag, msg): fails.append(f"[{tag}] {msg}")
def warn(tag, msg): warns.append(f"[{tag}] {msg}")

DESC_LIMIT = 1024   # Anthropic skill spec limit for frontmatter description

# Tokens that look like a skill reference but legitimately are not.
# Template artifact types / subtypes / ids are derived from templates/built-in
# at runtime (see VOCAB below); this set covers the rest of the repo vocabulary.
KNOWN_NON_SKILL_TOKENS = {
    # infrastructure / external
    "local-context", "grow-product-manager", "claude-code", "health-check",
    # Claude Design skills orchestrated by design-bridge (not our skills)
    "user-research", "research-synthesis", "ux-copy", "design-critique",
    "design-system", "accessibility-review", "design-handoff", "design-review",
    # product-reporter modes
    "sprint-plan", "sprint-review", "quarter-review", "initiative-status",
    "member-review", "goal-report",
    # onboarding deferred_steps / config keys
    "knowledge-library-setup", "obsidian-vault", "tableau-full", "custom-sections",
    "design-toolkits", "key-metrics", "analytics-extended", "tableau-mcp-required",
    # vault artifact types
    "ab-test-results", "competitive-analysis", "market-research", "ux-benchmark",
    "cjm-analysis", "task-breakdown", "project-overview", "focus-brief",
    "feedback-triage-report", "meeting-notes", "hypothesis-list",
}

# ---------------------------------------------------------------- inventories
skill_files = sorted(glob.glob(os.path.join(root, "skills", "*", "SKILL.md")))
if not skill_files:
    print(f"[!] No skills/*/SKILL.md found in {root}"); sys.exit(2)
SKILLS = {os.path.basename(os.path.dirname(p)) for p in skill_files}

# every reference/doc file, recursively (the old linter globbed one level only)
ref_files = glob.glob(os.path.join(root, "references", "**", "*.*"), recursive=True) + \
            glob.glob(os.path.join(root, "skills", "*", "references", "**", "*.*"), recursive=True)
REF_BASENAMES = {os.path.basename(p) for p in ref_files}
IGNORE_MD = {"local-context.md", "local-context.example.md", "SKILL.md", "README.md",
             "CHANGELOG.md", "library.md", "sources.md", "categories.md", "_registry.json",
             "board.html", "context-schema.md"}

def fm_block(text):
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n", text, re.S)
    return m.group(1) if m else None

def strip_code_fences(text):
    """Drop ``` fenced blocks — a '# comment' inside YAML is not an H1 heading."""
    return re.sub(r"^```.*?^```", "", text, flags=re.S | re.M)

def owning_skill_dir(path):
    """skills/<x>/references/**/f.md -> skills/<x>, so a doc can cite its siblings
    as `references/f.md` exactly the way SKILL.md does."""
    p = os.path.abspath(path)
    parts = p.split(os.sep)
    if "references" in parts:
        i = len(parts) - 1 - parts[::-1].index("references")
        if i >= 1 and parts[i - 2:i - 1] == ["skills"]:
            return os.sep.join(parts[:i])
    return None

# The repo's own template vocabulary — artifact types, subtypes and ids are
# kebab-case like skill names, so the ghost-skill check must know them.
VOCAB = set()
for tp in glob.glob(os.path.join(root, "templates", "built-in", "*", "*.md")):
    VOCAB.add(os.path.basename(os.path.dirname(tp)))
    b = fm_block(open(tp, encoding="utf-8").read()) or ""
    vals = {}
    for key in ("artifact_type", "subtype", "template_id", "id"):
        m = re.search(rf"^{key}:\s*(.+?)\s*$", b, re.M)
        if m:
            v = m.group(1).strip().strip('"').strip("'")
            if v and v != "null":
                VOCAB.add(v); vals[key] = v
    # skills also address templates as "{artifact_type}-{subtype}" (e.g. cjm-funnel)
    if "artifact_type" in vals and "subtype" in vals:
        VOCAB.add(f"{vals['artifact_type']}-{vals['subtype']}")

# ------------------------------------------- 1+2. frontmatter validity/fields
def scan_plain_scalar_hazards(block):
    """Detect YAML plain scalars that a strict parser rejects.

    Frontmatter is simple key: value. An unquoted (plain) value may not contain
    ': ' or ' #' — both terminate the scalar. This is the exact defect that made
    28/29 SKILL.md files unparseable by PyYAML/js-yaml while Claude Code's
    lenient parser accepted them.
    """
    hazards = []
    for line in block.split("\n"):
        m = re.match(r"^([a-zA-Z_-]+):\s*(.*)$", line)
        if not m:
            continue                      # continuation / list item / block scalar body
        key, val = m.group(1), m.group(2)
        if not val or val.startswith((">", "|")):
            continue                      # block scalar — colons are safe there
        if (val.startswith('"') and val.endswith('"') and len(val) > 1) or \
           (val.startswith("'") and val.endswith("'") and len(val) > 1):
            continue                      # quoted — safe
        if re.search(r":\s", val):
            hazards.append((key, "': ' in unquoted value"))
        if re.search(r"\s#", val):
            hazards.append((key, "' #' in unquoted value"))
    return hazards

try:
    import yaml
    HAVE_YAML = True
except ImportError:
    HAVE_YAML = False
    warn("frontmatter-yaml", "PyYAML absent — strict parse skipped, hazard scan still ran")

semver = re.compile(r"^\d+\.\d+\.\d+$")
for sf in skill_files:
    folder = os.path.basename(os.path.dirname(sf))
    text = open(sf, encoding="utf-8").read()
    block = fm_block(text)
    if not block:
        fail("frontmatter-yaml", f"{folder}: no YAML frontmatter"); continue

    for key, why in scan_plain_scalar_hazards(block):
        fail("frontmatter-yaml", f"{folder}: '{key}' — {why} (quote it or rephrase)")

    data = None
    if HAVE_YAML:
        try:
            data = yaml.safe_load(block)
        except Exception as e:
            fail("frontmatter-yaml", f"{folder}: strict YAML parse failed — {str(e).splitlines()[0]}")
    if data is None:                       # fall back to regex extraction
        def field(k):
            m = re.search(rf"^{k}:\s*(.+?)\s*$", block, re.M)
            return m.group(1).strip().strip('"').strip("'") if m else None
        data = {k: field(k) for k in ("name", "version", "description")}

    name, ver, desc = data.get("name"), str(data.get("version") or ""), str(data.get("description") or "")
    if not name: fail("frontmatter-fields", f"{folder}: no name")
    elif name != folder: fail("frontmatter-fields", f"{folder}: name '{name}' != folder")
    if not ver: fail("frontmatter-fields", f"{folder}: no version")
    elif not semver.match(ver): fail("frontmatter-fields", f"{folder}: version '{ver}' is not semver")
    if not desc: fail("frontmatter-fields", f"{folder}: no description")
    elif len(desc) > DESC_LIMIT:
        fail("frontmatter-fields", f"{folder}: description {len(desc)} chars > {DESC_LIMIT} limit")
    elif len(desc) < 40: warn("frontmatter-fields", f"{folder}: description is short (<40 chars)")

    # 3. inline skill_version must track the frontmatter
    for m in re.finditer(r'skill_version:\s*["\']?([\d.]+)', text):
        if ver and m.group(1) != ver:
            fail("skill-version-sync", f"{folder}: body skill_version '{m.group(1)}' != frontmatter '{ver}'")

# --------------------------------------------------------------- 4. ref paths
def path_exists(rel, skill_dir):
    """A `references/x.md` mention resolves at repo root OR skill-locally."""
    return os.path.isfile(os.path.join(root, rel)) or \
           (skill_dir and os.path.isfile(os.path.join(skill_dir, rel)))

# matches references/x.md, references/sub/x.md, templates/built-in/a/b-v1.md,
# skills/foo/references/x.yaml — i.e. multi-segment paths the old regex missed
PATH_RE = re.compile(r"\b((?:references|templates|testing|skills)/[\w./<>{}-]*\.(?:md|yaml|yml|json|html))")
for sf in skill_files:
    skill_dir = os.path.dirname(sf)
    folder = os.path.basename(skill_dir)
    text = open(sf, encoding="utf-8").read()
    for rel in sorted(set(PATH_RE.findall(text))):
        if re.search(r"[<>{}]", rel):
            # placeholder path — verify the directory instead of the file
            d = rel.split("<")[0].split("{")[0].rsplit("/", 1)[0]
            if not (os.path.isdir(os.path.join(root, d)) or (skill_dir and os.path.isdir(os.path.join(skill_dir, d)))):
                fail("ref-paths", f"{folder}: placeholder path '{rel}' — dir '{d}/' does not exist")
            continue
        if not path_exists(rel, skill_dir):
            fail("ref-paths", f"{folder}: path '{rel}' does not resolve")

# dangling backticked *.md inside reference bodies (recursive now)
for rp in ref_files:
    if not rp.endswith(".md"): continue
    t = open(rp, encoding="utf-8").read()
    own = owning_skill_dir(rp)
    for m in sorted(set(re.findall(r"`([\w-]+\.md)`", t))):
        if re.search(r"\d{4}-\d{2}-\d{2}", m): continue     # dated artifact example
        if m not in REF_BASENAMES and m not in IGNORE_MD:
            warn("ref-paths", f"{os.path.basename(rp)}: backticked '{m}' does not resolve")
    for line in t.split("\n"):
        for rel in sorted(set(PATH_RE.findall(line))):
            if re.search(r"[<>{}]", rel): continue
            if path_exists(rel, own): continue
            # an explicitly unwritten doc is a roadmap note, not a broken link
            if "(planned)" in line or "(TBD)" in line:
                warn("ref-paths", f"{os.path.basename(rp)}: '{rel}' marked planned — not written yet")
                continue
            fail("ref-paths", f"{os.path.basename(rp)}: path '{rel}' does not resolve")

# ------------------------------------------------------------ 5. ghost skills
# A backticked kebab-case token that is not a real skill, on a line that also
# names a real skill in backticks, is almost certainly a ghost chain target.
# Caught in the audit: `people-context` (a protocol, not a skill), `write-spec`.
KEBAB = re.compile(r"`([a-z][a-z0-9]*(?:-[a-z0-9]+)+)`")
for f in skill_files + [p for p in ref_files if p.endswith(".md")]:
    rel_name = os.path.relpath(f, root)
    for i, line in enumerate(strip_code_fences(open(f, encoding="utf-8").read()).split("\n"), 1):
        toks = set(KEBAB.findall(line))
        if not toks: continue
        real = toks & SKILLS
        if not real: continue
        for t in sorted(toks - SKILLS):
            if t in KNOWN_NON_SKILL_TOKENS or t in VOCAB: continue
            if f"{t}.md" in REF_BASENAMES or f"{t}.yaml" in REF_BASENAMES: continue
            if t.endswith(("-protocol", "-model", "-map", "-frameworks", "-core",
                           "-v1", "-setup", "-notes", "-arcv", "-letter", "-plan",
                           "-profile", "-index", "-3t5f")): continue
            if t.startswith(("builtin-", "cjm-builtin", "templates-")): continue
            fail("ghost-skill", f"{rel_name}:{i}: '{t}' is not a skill (line also cites {sorted(real)[0]})")

# ------------------------------------------------------------- 6. stale names
# Renames are only complete when the old identifier is gone from live docs.
# CHANGELOG is history and README/validators may cite a rename deliberately.
STALE = {
    "team-ops-reporter": "product-reporter",
    "feature-task-creator": "task-creator",
    "Feature-task-creator": "Task-creator",
}
for f in skill_files + [p for p in ref_files if p.endswith(".md")] + \
         glob.glob(os.path.join(root, "templates", "**", "*.md"), recursive=True):
    rel_name = os.path.relpath(f, root)
    t = open(f, encoding="utf-8").read()
    for old, new in STALE.items():
        for i, line in enumerate(t.split("\n"), 1):
            if old in line and "renamed" not in line.lower() and "formerly" not in line.lower():
                fail("stale-names", f"{rel_name}:{i}: stale '{old}' (renamed to '{new}')")

# ----------------------------------------------------------- 7. duplicate H1
# vault-protocol.md and persistent-storage.md each contained their whole content
# twice: a new version was prepended instead of replacing the old one.
for rp in ref_files:
    if not rp.endswith(".md"): continue
    # '#' inside a fenced block is a code comment, not a heading
    lines = strip_code_fences(open(rp, encoding="utf-8").read()).split("\n")
    h1s = [i for i, l in enumerate(lines, 1) if l.startswith("# ")]
    if len(h1s) > 1:
        fail("duplicate-h1", f"{os.path.basename(rp)}: {len(h1s)} H1 headings (lines {h1s}) — doc likely contains itself twice")

# -------------------------------------------------------- 8. README versions
README = os.path.join(root, "README.md")
README_ALIASES = {                       # README display name -> folder
    "diagram-&-prototype-creator": "diagram-prototyper",
}
def slugify(n): return re.sub(r"\s+", "-", n.strip().lower())
if os.path.isfile(README):
    rt = open(README, encoding="utf-8").read()
    fm_versions = {}
    for sf in skill_files:
        folder = os.path.basename(os.path.dirname(sf))
        b = fm_block(open(sf, encoding="utf-8").read())
        m = re.search(r"^version:\s*([\d.]+)", b, re.M)
        if m: fm_versions[folder] = m.group(1)
    claims = [(m.group(1), m.group(2), m.start()) for m in
              re.finditer(r"^### \d+\.\s+([^(\n]+?)\s+\(v([\d.]+)\)", rt, re.M)]
    claims += [(m.group(1), m.group(2), m.start()) for m in
               re.finditer(r"^\|\s*([A-Z][A-Za-z &-]+?)\s*\|\s*v([\d.]+)\s*\|", rt, re.M)]
    for disp, claimed, pos in claims:
        slug = README_ALIASES.get(slugify(disp), slugify(disp))
        if slug not in fm_versions:
            warn("readme-versions", f"README names '{disp}' -> '{slug}', which is not a skill folder")
            continue
        if claimed != fm_versions[slug]:
            line = rt[:pos].count("\n") + 1
            fail("readme-versions", f"README.md:{line}: '{disp}' claims v{claimed}, frontmatter is v{fm_versions[slug]}")
    for folder in sorted(SKILLS):
        if folder not in {README_ALIASES.get(slugify(d), slugify(d)) for d, _, _ in claims}:
            warn("readme-versions", f"skill '{folder}' has no versioned README entry")

# ------------------------------------------------------------- 9. org data
# The example file shipped a real team roster, board id, epic keys and a named
# VIP to a public repo. Shipped files must carry placeholders only.
ORG_TOKENS = re.compile(r"\b(<org-token>|<org-token>|<org-token>)\b", re.I)
PLACEHOLDER_HOSTS = ("your-org", "your-domain", "company", "example")
scan_targets = [os.path.join(root, "local-context.example.md")] + \
               glob.glob(os.path.join(root, "templates", "**", "*.md"), recursive=True) + \
               [p for p in ref_files if p.endswith((".md", ".yaml"))] + skill_files
for f in scan_targets:
    if not os.path.isfile(f): continue
    rel_name = os.path.relpath(f, root)
    for i, line in enumerate(open(f, encoding="utf-8").read().split("\n"), 1):
        m = ORG_TOKENS.search(line)
        if m: fail("org-data", f"{rel_name}:{i}: internal identifier '{m.group(1)}' — use a placeholder")
        for host in re.findall(r"([\w-]+)\.atlassian\.net", line):
            if not any(p in host for p in PLACEHOLDER_HOSTS):
                fail("org-data", f"{rel_name}:{i}: real Atlassian host '{host}.atlassian.net' — use your-org")
        # letter-only TLD so version markers like `template-id@0.1` don't match
        for email in re.findall(r"[\w.+-]+@([\w-]+(?:\.[\w-]+)*\.[a-zA-Z]{2,})", line):
            if not any(p in email for p in PLACEHOLDER_HOSTS):
                fail("org-data", f"{rel_name}:{i}: real-looking email domain '{email}' — use example.com")

# A linter cannot know that "Surname1" is a real person, so the roster leak needs
# a positive rule instead of a denylist: the example file carries placeholders only.
PLACEHOLDER_NAME = re.compile(r"^(Surname\d*|Name\d*|Firstname|Lastname|Person\d*|Member\d*|"
                              r"Dev\d*|TL|QA|<[^>]+>|\.\.\.)$")
example = os.path.join(root, "local-context.example.md")
if os.path.isfile(example):
    for i, line in enumerate(open(example, encoding="utf-8").read().split("\n"), 1):
        m = re.search(r"members:\s*\[([^\]]*)\]", line)
        if not m: continue
        for nm in [x.strip() for x in m.group(1).split(",") if x.strip()]:
            if not PLACEHOLDER_NAME.match(nm):
                fail("org-data", f"local-context.example.md:{i}: '{nm}' is not a placeholder "
                                 f"(use Surname1/Name1/<role>) — the example must never carry a real roster")

# --------------------------------------------------------- 10. deck subtypes
# `feature` vs `feature-concept`: the yaml key, the built-in template subtype,
# and the callers' payloads must agree or the lookup silently misses.
deck_yaml = os.path.join(root, "skills", "design-bridge", "references", "deck-subtypes.yaml")
if os.path.isfile(deck_yaml):
    yt = open(deck_yaml, encoding="utf-8").read()
    body = yt.split("subtypes:", 1)[1] if "subtypes:" in yt else ""
    yaml_keys = set(re.findall(r"^  ([a-z][a-z0-9-]*):\s*$", body, re.M))
    tpl_subtypes = set()
    for tp in glob.glob(os.path.join(root, "templates", "built-in", "presentation", "*.md")):
        m = re.search(r"^subtype:\s*(.+?)\s*$", open(tp, encoding="utf-8").read(), re.M)
        if m: tpl_subtypes.add(m.group(1).strip())
    for k in sorted(yaml_keys - tpl_subtypes):
        fail("deck-subtypes", f"deck-subtypes.yaml key '{k}' has no built-in template with that subtype")
    for s in sorted(tpl_subtypes - yaml_keys):
        warn("deck-subtypes", f"built-in presentation subtype '{s}' has no deck-subtypes.yaml outline")

# -------------------------------------------------------------------- report
print(f"== Static lint: {root} ==")
print(f"skills: {len(skill_files)} | reference files: {len(ref_files)} | checks: {len(CHECKS.strip().splitlines())}")
print(f"\nFAIL: {len(fails)}")
for f in fails: print("  ✗", f)
print(f"\nWARN: {len(warns)}")
for w in warns: print("  •", w)
print("\nRESULT:", "GREEN ✅" if not fails else "RED ❌ (blockers present)")
sys.exit(1 if fails else 0)
