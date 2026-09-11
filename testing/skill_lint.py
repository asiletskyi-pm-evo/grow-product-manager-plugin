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
 9. org-data             real org identifiers in shipped example/templates/refs/agents/commands
10. deck-subtypes        deck-subtypes.yaml keys == built-in template subtypes
11. vault-types          every vault_save type is in the taxonomy AND TYPE_FOLDER_MAP
12. artifact-types       every Step T artifact_type is in the template-protocol enum
13. chain-contracts      a claimed inbound edge (<- X) exists on X's side too
14. vault-paths          every example vault path matches TYPE_FOLDER_MAP's layout
15. builtin-subtypes     a declared subtype resolves to a built-in filename
16. org-signature        a team/org name cited as the authority behind a rule or example
17. example-locale       non-Latin examples, or an output language hardcoded in a doc
18. example-keys         example issue/space keys outside the placeholder vocabulary
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
    # experiment-tracker lifecycle states
    "awaiting-readout", "hypothesis-backlog",
    # design-toolkit capability core-enum (design-toolkit-protocol.md §3)
    "hi-fi-prototype", "screen-generation", "ds-tokens", "figma-write",
    "code-first-research",
    # template-library modes
    "add-language", "add-template", "list-templates", "edit-template",
    # flow-walkthrough vocabulary (app-drive-protocol.md): source marker, surfaces, drive levels
    "walkthrough-local", "iphone-on-mac", "android-adb", "ios-simulator", "desktop-background",
    # v3.2.0: configurator deferred step id + write-boundary values
    "test-accounts", "stop-before-irreversible", "sandbox-confirm", "sandbox-auto", "read-only",
    # v3.3.0: product-landscape roles and source types
    "direct-competitor", "scan-mac", "scan-adb", "scan-iphone-on-mac", "appstore-api", "play-web",
}

# ---------------------------------------------------------------- inventories
skill_files = sorted(glob.glob(os.path.join(root, "skills", "*", "SKILL.md")))
if not skill_files:
    print(f"[!] No skills/*/SKILL.md found in {root}"); sys.exit(2)
SKILLS = {os.path.basename(os.path.dirname(p)) for p in skill_files}

# every reference/doc file, recursively (the old linter globbed one level only)
ref_files = glob.glob(os.path.join(root, "references", "**", "*.*"), recursive=True) + \
            glob.glob(os.path.join(root, "skills", "*", "references", "**", "*.*"), recursive=True)
# v2.5.0: agents/ and commands/ ship too — they are prose the model reads, so every
# org-leak / locale / stale-name rule that applies to a reference applies to them.
component_files = sorted(glob.glob(os.path.join(root, "agents", "*.md")) +
                         glob.glob(os.path.join(root, "commands", "*.md")) +
                         glob.glob(os.path.join(root, "scripts", "*.py")) +
                         glob.glob(os.path.join(root, "scripts", "*.sh")))
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

# The artifact_type enum is vocabulary too — including members that ship no
# built-in template yet (e.g. delegation-audit), and members that share a name
# with a skill (performance-review). Parsed here so both ghost-skill and
# artifact-types read the same single source.
ARTIFACT_ENUM = set()
_proto = os.path.join(root, "references", "template-protocol.md")
if os.path.isfile(_proto):
    _pt = open(_proto, encoding="utf-8").read()
    _em = re.search(r"### artifact_type enum.*?\n(.*?)(?=\n### )", _pt, re.S)
    if _em:
        # Only the "**<name> contour:**" lines carry enum members. Slurping every
        # backticked token in the section also swallowed the explanatory note, so
        # `template-library`, `focus-advisor` etc. became legal artifact types and
        # the check could not reject them.
        _rows = re.findall(r"^\*\*[^*]*contour:\*\*(.*)$", _em.group(1), re.M)
        if not _rows:
            warn("artifact-types", "template-protocol.md: artifact_type enum has no '**… contour:**' rows")
        for _row in _rows:
            ARTIFACT_ENUM |= set(re.findall(r"`([a-z0-9-]+)`", _row))
        VOCAB |= ARTIFACT_ENUM

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

# The strict parse catches frontmatter the hazard scan cannot (e.g. an unbalanced
# quote), so on the runner its absence must be a blocker, not a note that nothing
# gates on. CI sets GROW_LINT_REQUIRE_YAML=1; locally a missing PyYAML stays a warn.
try:
    import yaml
    HAVE_YAML = True
except ImportError:
    HAVE_YAML = False
    if os.environ.get("GROW_LINT_REQUIRE_YAML") == "1":
        fail("frontmatter-yaml", "PyYAML absent but GROW_LINT_REQUIRE_YAML=1 — "
                                 "the strict parse must run in CI (pip install pyyaml)")
    else:
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
    # Optional `v` prefix: `skill_version: v0.9.0` used to slip past the regex
    # entirely, so a desync in that form was invisible rather than reported.
    for m in re.finditer(r'skill_version:\s*["\']?v?([\d.]+)', text):
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
# A chain line names its target and often nothing else, so requiring a real skill
# on the same line blinds this check to the ghosts it exists to catch. On lines
# that explicitly hand work to a skill, a lone unknown token is enough to fail.
# Bare arrows are deliberately NOT markers: in these docs "→" overwhelmingly means
# "maps to" (keyword → category, config → MCP tool), not "chains to".
CHAIN_MARKER = re.compile(r"(\bchain(s|ed)?\s+(to|into)\b|\binvoke(s|d)?\b|\bdelegat\w*\s+to\b|"
                          r"\bhand(s)?[ -]off\s+to\b|\broute(s|d)?\s+to\b|"
                          r"виклич|делегу)", re.I)
for f in skill_files + [p for p in ref_files if p.endswith(".md")]:
    rel_name = os.path.relpath(f, root)
    for i, line in enumerate(strip_code_fences(open(f, encoding="utf-8").read()).split("\n"), 1):
        toks = set(KEBAB.findall(line))
        if not toks: continue
        real = toks & SKILLS
        if not real and not CHAIN_MARKER.search(line): continue
        for t in sorted(toks - SKILLS):
            if t in KNOWN_NON_SKILL_TOKENS or t in VOCAB: continue
            if f"{t}.md" in REF_BASENAMES or f"{t}.yaml" in REF_BASENAMES: continue
            if t.endswith(("-protocol", "-model", "-map", "-frameworks", "-core",
                           "-v1", "-setup", "-notes", "-arcv", "-letter", "-plan",
                           "-profile", "-index", "-3t5f")): continue
            if t.startswith(("builtin-", "cjm-builtin", "templates-")): continue
            ctx = f"line also cites {sorted(real)[0]}" if real else "on a chain line"
            fail("ghost-skill", f"{rel_name}:{i}: '{t}' is not a skill ({ctx})")

# ------------------------------------------------------------- 6. stale names
# Renames are only complete when the old identifier is gone from live docs.
# CHANGELOG is history; a deliberate citation ("renamed from X", "formerly X")
# is exempted per-line below, which is what lets README be scanned too — it is
# the most public file a stale name can survive in.
STALE = {
    "team-ops-reporter": "product-reporter",
    "feature-task-creator": "task-creator",
    "Feature-task-creator": "Task-creator",
}
for f in skill_files + [p for p in ref_files if p.endswith(".md")] + component_files + \
         glob.glob(os.path.join(root, "templates", "**", "*.md"), recursive=True) + \
         [os.path.join(root, "README.md")]:
    if not os.path.isfile(f): continue
    rel_name = os.path.relpath(f, root)
    t = open(f, encoding="utf-8").read()
    for old, new in STALE.items():
        for i, line in enumerate(t.split("\n"), 1):
            low = line.lower()
            # case-insensitive: "Team-Ops-Reporter" in a heading is just as stale
            if old.lower() in low and "renamed" not in low and "formerly" not in low:
                fail("stale-names", f"{rel_name}:{i}: stale '{old}' (renamed to '{new}')")

# ----------------------------------------------------------- 7. duplicate H1
# vault-protocol.md and persistent-storage.md each contained their whole content
# twice: a new version was prepended instead of replacing the old one.
# SKILL.md files are included too: they are the highest-value docs in the repo,
# and a doubled SKILL.md was invisible here while a doubled reference was not.
for rp in [p for p in ref_files if p.endswith(".md")] + skill_files:
    # '#' inside a fenced block is a code comment, not a heading
    body = open(rp, encoding="utf-8").read()
    if rp in skill_files:
        body = body[len(fm_block(body)):] if fm_block(body) else body
    lines = strip_code_fences(body).split("\n")
    h1s = [i for i, l in enumerate(lines, 1) if l.startswith("# ")]
    if len(h1s) > 1:
        label = os.path.relpath(rp, root)
        fail("duplicate-h1", f"{label}: {len(h1s)} H1 headings (lines {h1s}) — doc likely contains itself twice")

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

    # README counts vs reality. v2.0.1 corrected "24 seed templates" but not the
    # list under it, which stayed at 17 — so the count and its own enumeration
    # disagreed for a whole release. Check the claim, the list, and the disk.
    builtins = glob.glob(os.path.join(root, "templates", "built-in", "*", "*.md"))
    m = re.search(r"^(\d+)\s+seed templates", rt, re.M)
    if m:
        claimed_n, actual_n = int(m.group(1)), len(builtins)
        if claimed_n != actual_n:
            fail("readme-versions", f"README claims {claimed_n} seed templates; "
                                    f"templates/built-in/ has {actual_n}")
        listed = len(re.findall(r"^- `[a-z0-9-]+/[a-z0-9-]+-v\d+`", rt[m.start():], re.M))
        if listed != actual_n:
            fail("readme-versions", f"README enumerates {listed} seed templates but claims "
                                    f"{claimed_n} and ships {actual_n} — list and count must agree")

# ------------------------------------------------------------- 9. org data
# The example file shipped a real team roster, board id, epic keys and a named
# VIP to a public repo. Shipped files must carry placeholders only.
#
# The checks below are deliberately **generic** — they describe the *shape* of a
# leak (a real host, a real email domain, a name that isn't a placeholder), not
# one organization's vocabulary. An earlier version hardcoded this repo's own org
# tokens into a denylist, which (a) contradicted the plugin's own rule that no
# org-specific value ships in the repo, and (b) put the very strings it forbade
# into the file forbidding them.
#
# To also catch your own org's identifiers, drop them one-per-line into
# `testing/org-tokens.local` — gitignored, so the tokens never ship. Absent
# (the CI case), the generic checks below still run.
#
# The denylist is OPTIONAL, and an optional layer that nobody notices is absent
# is a layer that does not run: the four leaks of 2026-07-30 shipped while this
# file did not exist on any machine. Its absence is now reported, and the
# shape-based checks 16-18 below cover the same defect class without it.
ORG_TOKENS = None
_tokens_file = os.path.join(root, "testing", "org-tokens.local")
if os.path.isfile(_tokens_file):
    _toks = [l.strip() for l in open(_tokens_file, encoding="utf-8")
             if l.strip() and not l.startswith("#")]
    if _toks:
        # Word-boundaried, not bare substring: a short team acronym is a substring
        # of ordinary English (a 3-letter token inside "offset", "settings"), and a
        # denylist that fires 40 times on the first run is a denylist the
        # maintainer deletes. Boundaries are added only where the token's own edge
        # is a word character, so "example.com" or ".corp" still match mid-token.
        def _bounded(t):
            e = re.escape(t)
            return (r"\b" if t[:1].isalnum() else "") + e + (r"\b" if t[-1:].isalnum() else "")
        ORG_TOKENS = re.compile("|".join(_bounded(t) for t in _toks), re.I)
    else:
        warn("org-data", "testing/org-tokens.local exists but is empty — the org denylist is not running")
else:
    warn("org-data", "testing/org-tokens.local absent — the org denylist is not running "
                     "(copy org-tokens.local.example and list your team/org names; it is gitignored)")

# Whole-label match: "mycompany.io" must NOT pass because "company" is a substring
# of "mycompany" (that bug shipped a real domain past this check).
PLACEHOLDER_HOSTS = ("your-org", "your-domain", "company", "example", "internal-gitlab-host",
                     "acme", "localhost")
def is_placeholder_host(host):
    # A label matches whole ("company.com") or as a hyphen-part ("example-corp.com").
    # "mycompany.io" must not match "company" — that is the bug this replaces.
    for label in host.lower().split("."):
        if label in PLACEHOLDER_HOSTS: return True
        if any(part in PLACEHOLDER_HOSTS for part in label.split("-")): return True
    return False

# An instance UUID (Atlassian cloud id, Jira Team object id) is org data in the
# same way a hostname is, and no generic "is it real" test exists — so any
# literal UUID in a shipped file is a leak by shape. Placeholders use <angle>.
UUID_RE = re.compile(r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b", re.I)
# National company registry ids (UA legal entity), 8 digits after the label.
REGISTRY_RE = re.compile(r"(ЄДРПОУ|EDRPOU|ІПН|VAT\s*ID)\D{0,5}\d{8}", re.I)
# Internal hosts that are not Atlassian: foo.corp, jira.internal, host.intra …
# `.local` is deliberately NOT a suffix here: it is the repo's own convention for
# gitignored config (testing/org-tokens.local), so it collides with filenames.
INTERNAL_HOST_RE = re.compile(r"\b(?:[\w-]+\.)+(?:corp|internal|lan|intra)\b", re.I)
VCS_HOST_RE = re.compile(r"\b(?:gitlab|jira|confluence|jenkins|grafana|tableau)\.(?:[\w-]+\.)+[a-z]{2,}\b", re.I)

# README and the test fixtures ship too: README is the most public file in the
# repo, and fixtures are realistic briefs where org context creeps in naturally.
scan_targets = [os.path.join(root, "local-context.example.md"),
                os.path.join(root, "README.md")] + \
               glob.glob(os.path.join(root, "templates", "**", "*.md"), recursive=True) + \
               glob.glob(os.path.join(root, "testing", "**", "*.md"), recursive=True) + \
               [p for p in ref_files if p.endswith((".md", ".yaml"))] + skill_files + component_files
for f in scan_targets:
    if not os.path.isfile(f): continue
    rel_name = os.path.relpath(f, root)
    for i, line in enumerate(open(f, encoding="utf-8").read().split("\n"), 1):
        if ORG_TOKENS:
            m = ORG_TOKENS.search(line)
            if m: fail("org-data", f"{rel_name}:{i}: org identifier '{m.group(0)}' — use a placeholder")
        for host in re.findall(r"([\w-]+)\.atlassian\.net", line):
            if not is_placeholder_host(host):
                fail("org-data", f"{rel_name}:{i}: real Atlassian host '{host}.atlassian.net' — use your-org")
        # letter-only TLD so version markers like `template-id@0.1` don't match
        for email in re.findall(r"[\w.+-]+@([\w-]+(?:\.[\w-]+)*\.[a-zA-Z]{2,})", line):
            if not is_placeholder_host(email):
                fail("org-data", f"{rel_name}:{i}: real-looking email domain '{email}' — use example.com")
        m = UUID_RE.search(line)
        if m: fail("org-data", f"{rel_name}:{i}: literal UUID '{m.group(0)}' — instance/team ids "
                               f"live in local-context; ship <team-uuid>/<cloud-id>")
        m = REGISTRY_RE.search(line)
        if m: fail("org-data", f"{rel_name}:{i}: company registry id '{m.group(0)}' — never ship a legal entity id")
        for rx, what in ((INTERNAL_HOST_RE, "internal hostname"), (VCS_HOST_RE, "internal service host")):
            m = rx.search(line)
            if m and not is_placeholder_host(m.group(0)):
                fail("org-data", f"{rel_name}:{i}: {what} '{m.group(0)}' — use a placeholder host")

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

# ---------------------------------------------------- 16. org signature
# A leak does not have to look like a hostname. The 2026-07-30 audit found four
# lines that named the maintainer's own team as the authority behind a rule or an
# example: "per <Team> convention", "(<Team> formatting rules)", a section titled
# "Reference example (<Team> Q3 2026…)", and "validated by a run of Q3 <Team>".
# Every check above was blind to them — the token is an ordinary word, and the
# denylist layer that would have named it is optional and was absent everywhere.
#
# The rule that catches them is positional, not lexical. In a shipped file the
# authority behind a convention is the plugin itself, the user's own
# `local-context.md`, or a named vendor — never a proper noun the reader has no
# way to look up. And an example is never signed with a team and a quarter: a
# reader outside that team cannot verify it, and a reader inside it will copy the
# team's habits as if they were the plugin's rules.
KNOWN_PROPER = {
    # vendors / tools / formats that legitimately own a convention
    "jira", "confluence", "atlassian", "github", "gitlab", "git", "figma", "miro",
    "slack", "google", "claude", "anthropic", "tableau", "fireflies", "obsidian",
    "notion", "linear", "mermaid", "markdown", "commonmark", "python", "pillow",
    "semver", "iso", "json", "yaml", "html", "css", "chatgpt", "gemini",
    "notebooklm", "draw", "keep", "conventional", "unicode", "rfc",
    # ordinary words that can sit in front of a convention noun
    "the", "this", "that", "these", "those", "our", "your", "their", "its", "a",
    "an", "one", "same", "each", "every", "no", "any", "all", "both", "other",
    "team", "company", "org", "project", "product", "plugin", "skill", "template",
    "vault", "repo", "repository", "release", "commit", "branch", "file", "folder",
    "quality", "marking", "naming", "style", "data", "best", "industry", "local",
    "default", "standard", "house", "output", "input", "source", "target",
    # the repo's own method acronyms
    "arcv", "cjm", "gtd", "ice", "rice", "smart", "smartcbp", "okr", "nvc",
    "roaip", "pm", "ux", "ui", "prd", "adr", "moc", "wcag", "bpmn",
    # date placeholders
    "yyyy", "yy", "mm", "dd", "hh", "q1", "q2", "q3", "q4",
}
PN = r"([A-Z][A-Za-z0-9.&-]{1,15})"
AUTH_NOUN = (r"(?:conventions?|rules?|standards?|formats?|formatting|process(?:es)?|"
             r"polic(?:y|ies)|guidelines?|practices?|naming|style)")
SIGNATURE_RULES = [
    (re.compile(rf"\b(?:per|as per|following|according to)\s+(?:the\s+)?{PN}\s+{AUTH_NOUN}\b"),
     "cites '{t}' as the authority behind a rule — name the config key "
     "(`local-context.md`) or the vendor instead"),
    (re.compile(rf"\(\s*{PN}\s+{AUTH_NOUN}\s*\)"),
     "qualifies a rule with '{t}' — a reader outside that org cannot look it up"),
    (re.compile(rf"\b{PN}\s+(?:formatting|naming|style|report)\s+rules?\b"),
     "attributes rules to '{t}' — read them from `local-context.md` instead"),
    (re.compile(rf"\b{PN}\s+Q[1-4]\b"),
     "signs an example with '{t}' + a quarter — anonymize it "
     "('anonymized from a real quarterly run')"),
    (re.compile(rf"\bQ[1-4]\s+{PN}\b"),
     "signs an example with a quarter + '{t}' — anonymize it"),
    (re.compile(rf"\b(?:verified|validated|measured|confirmed|observed|piloted|adopted)\s+"
                rf"(?:by|at|in|for|with)\s+(?:the\s+)?{PN}\s+"
                rf"(?:team|squad|tribe|department|unit|org|crew)\b"),
     "attributes an example to the '{t}' team — anonymize it"),
]
for f in scan_targets:
    if not os.path.isfile(f): continue
    rel_name = os.path.relpath(f, root)
    for i, line in enumerate(open(f, encoding="utf-8").read().split("\n"), 1):
        for rx, msg in SIGNATURE_RULES:
            for m in rx.finditer(line):
                t = m.group(1)
                if t.lower() in KNOWN_PROPER: continue
                if t in SKILLS or t in VOCAB: continue
                fail("org-signature", f"{rel_name}:{i}: " + msg.format(t=t))

# ---------------------------------------------------- 17. example locale
# Two ways a shipped doc stops being universal. First: a schema example written
# in the maintainer's own language — the glossary schema shipped sample terms,
# synonyms and definitions in one team's language, so every other user read a
# format spec they could not use as a model.
#
# Scope is deliberately **fenced blocks only**. Trigger phrases in prose
# («проведи дебати»), Jira status synonyms and quoted output lines are the
# plugin's bilingual surface by design; a fenced block is a machine-readable
# example that the model copies literally, so its values must be neutral.
# Localized wording belongs in `templates/` (deliberately bilingual) and in the
# user's own `~/.grow-pm/` files.
#
# Second: a hardcoded output language. "Language: <Lang> by default" pinned one
# team's language into a skill that has `user.language` for exactly this.
NON_LATIN = re.compile(r"[Ѐ-ӿ֐-׿؀-ۿ一-鿿぀-ヿ]")
locale_targets = [p for p in ref_files if p.endswith((".md", ".yaml"))] + skill_files + component_files
for f in locale_targets:
    rel_name = os.path.relpath(f, root)
    in_fence = False
    for i, line in enumerate(open(f, encoding="utf-8").read().split("\n"), 1):
        if line.lstrip().startswith("```"):
            in_fence = not in_fence; continue
        if not in_fence: continue
        m = NON_LATIN.search(line)
        if m:
            fail("example-locale", f"{rel_name}:{i}: non-Latin sample value ('{m.group(0)}…') inside a "
                                   f"code block — a format example must be language-neutral English; "
                                   f"localized wording belongs in templates/ or the user's own files")

LANGS = ("Ukrainian|Russian|Polish|German|French|Spanish|Italian|Portuguese|Turkish|"
         "Chinese|Japanese|Korean|Arabic|Hebrew|Dutch|Czech|Slovak|Hungarian|Romanian|"
         "Bulgarian|Serbian|Croatian|Greek|Swedish|Norwegian|Danish|Finnish|Kazakh|"
         "Georgian|Armenian|Hindi|Vietnamese|Thai|Indonesian")
LANG_DEFAULT_RE = re.compile(
    rf"\b(?:{LANGS})\b[^.\n]{{0,30}}\bby default\b|"
    rf"\bdefaults?\s*(?:to|=|:)\s*(?:{LANGS})\b|"
    rf"\b(?:always|only)\s+(?:write|answer|respond|output|render)\w*\s+(?:in\s+)?(?:{LANGS})\b", re.I)
for f in scan_targets:
    if not os.path.isfile(f): continue
    rel_name = os.path.relpath(f, root)
    for i, line in enumerate(open(f, encoding="utf-8").read().split("\n"), 1):
        m = LANG_DEFAULT_RE.search(line)
        if m:
            fail("example-locale", f"{rel_name}:{i}: '{m.group(0).strip()}' hardcodes an output "
                                   f"language — read it from `user.language` in local-context")

# ------------------------------------------------------ 18. example keys
# The repo has one placeholder vocabulary — PROJ-1234 for issues, SPACE for a
# Confluence space, example.com for hosts, "Product 1" for a product. A real key
# in an example is both an org leak and a broken example: the reader cannot run
# it, and the model imitating the doc will address a project that is not theirs.
PLACEHOLDER_ISSUE_KEYS = {"PROJ", "PROJKEY", "EPICKEY", "ISSUEKEY", "KEY"}
PLACEHOLDER_SPACE_KEYS = {"SPACE", "SPACEKEY"}
# 4+ letters: real project keys are rarely shorter, and 2-3 letter prefixes are
# this repo's step ids (GB-1, RM-2, FR-3) — matching those would drown the check.
ISSUE_KEY_RE = re.compile(r"\b([A-Z][A-Z0-9]{3,9})-\d+\b")
SPACE_KEY_RE = re.compile(r"(?:confluence:|/wiki/spaces/|spaces/|space[ _-]?key[\"']?\s*[:=]\s*[\"']?)([A-Z][A-Z0-9]{1,9})\b")
for f in scan_targets:
    if not os.path.isfile(f): continue
    rel_name = os.path.relpath(f, root)
    for i, line in enumerate(open(f, encoding="utf-8").read().split("\n"), 1):
        for m in ISSUE_KEY_RE.finditer(line):
            k = m.group(1)
            if k in PLACEHOLDER_ISSUE_KEYS or k in VOCAB: continue
            fail("example-keys", f"{rel_name}:{i}: example issue key '{m.group(0)}' — "
                                 f"use the placeholder project (PROJ-1234)")
        for m in SPACE_KEY_RE.finditer(line):
            k = m.group(1)
            if k in PLACEHOLDER_SPACE_KEYS: continue
            fail("example-keys", f"{rel_name}:{i}: example Confluence space '{k}' — "
                                 f"use the placeholder space (SPACE)")

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

# --------------------------------------------------------- 11. vault types
# A type absent from TYPE_FOLDER_MAP has no destination — vault_save cannot
# resolve a folder for it. feedback-triage, report-3t5f, presentation, prototype,
# handoff and the whole People contour were all being saved to undefined types.
schema_p = os.path.join(root, "references", "vault-schema.md")
if os.path.isfile(schema_p):
    st = open(schema_p, encoding="utf-8").read()
    m = re.search(r"TYPE_FOLDER_MAP Reference\s*```json\s*(\{.*?\})\s*```", st, re.S)
    folder_map = {}
    if m:
        # A duplicated key is last-wins in json.loads, so one type quietly losing
        # its folder would parse clean. Reject dupes explicitly.
        def _no_dupes(pairs):
            seen = {}
            for k, v in pairs:
                if k in seen:
                    fail("vault-types", f"vault-schema.md: TYPE_FOLDER_MAP has duplicate key "
                                        f"'{k}' ('{seen[k]}' vs '{v}') — last-wins would hide one")
                seen[k] = v
            return seen
        try:
            folder_map = json.loads(m.group(1), object_pairs_hook=_no_dupes)
        except Exception as e:
            fail("vault-types", f"vault-schema.md: TYPE_FOLDER_MAP is not valid JSON — {e}")
    else:
        fail("vault-types", "vault-schema.md: TYPE_FOLDER_MAP Reference block not found")

    # taxonomy rows: | type | skill | folder | description |
    taxonomy = set(re.findall(r"^\|\s*([a-z][a-z0-9-]+)\s*\|[^|]*\|\s*[A-Z][\w/{}-]*\s*\|", st, re.M))
    for t in sorted(taxonomy - set(folder_map)):
        fail("vault-types", f"vault-schema.md: type '{t}' is in the taxonomy but missing from TYPE_FOLDER_MAP")
    for t in sorted(set(folder_map) - taxonomy):
        warn("vault-types", f"vault-schema.md: TYPE_FOLDER_MAP has '{t}' with no taxonomy row")

    # What the skills actually save.
    # Two passes, because a strict `vault_save({ type: "literal"` regex silently
    # skipped every call that wraps the value in prose — e.g.
    #   type: <per research type: "competitive-analysis" | "market-research">
    # which left three real types unvalidated. Pass 2 takes any vault_save line
    # and checks every quoted token between `type:` and the next key.
    SAVE_RE = re.compile(r'vault_save\(\{\s*type:\s*((?:"[a-z0-9-]+"\s*\|?\s*)+)')
    SAVE_LINE_RE = re.compile(r'vault_save\(.*?\btype:\s*([^,}\n]*)')
    # A variable stands in for a runtime-computed type — uncheckable by design.
    VAR_TYPE_RE = re.compile(r'^[a-z_][a-z0-9_]*$')
    for sf in skill_files:
        folder = os.path.basename(os.path.dirname(sf))
        text = open(sf, encoding="utf-8").read()
        seen = set()
        for m2 in SAVE_RE.finditer(text):
            for t in re.findall(r'"([a-z0-9-]+)"', m2.group(1)):
                seen.add((t, m2.start()))
        for m2 in SAVE_LINE_RE.finditer(text):
            frag = m2.group(1)
            for t in re.findall(r'["\']([a-z0-9-]+)["\']', frag):
                seen.add((t, m2.start()))
            bare = frag.strip().strip("`")
            if bare and not VAR_TYPE_RE.match(bare) and not re.search(r'["\'<]', bare):
                warn("vault-types", f"{folder}: vault_save type '{bare}' is neither a quoted "
                                    f"literal nor a variable — cannot be validated")
        for t, pos in sorted(seen, key=lambda x: x[1]):
            if t not in folder_map:
                line = text[:pos].count("\n") + 1
                fail("vault-types", f"{folder}:{line}: saves type '{t}', which is not in TYPE_FOLDER_MAP")

    # -------------------------------------------------------- 14. vault paths
    # The schema states one path rule, then its own MOC templates and the
    # protocol's examples contradicted it: product ABOVE the area subfolder
    # ([[CJM/mobile-app/health-checks/…]] when the map says CJM/health-checks/),
    # links with no key level at all, and an [[Hypotheses/archive/…]] folder the
    # schema forbids. Those examples are what the model imitates at save time, so
    # a wrong example writes wrong artifacts. Check them against the map.
    AREAS = sorted({v.strip("/") for v in folder_map.values()}, key=len, reverse=True)
    MULTI = [a for a in AREAS if "/" in a]          # e.g. CJM/health-checks
    TOP_OF_MULTI = {a.split("/")[0] for a in MULTI} # e.g. CJM
    SUBS_OF = {}
    for a in MULTI:
        SUBS_OF.setdefault(a.split("/")[0], set()).add(a.split("/", 1)[1])
    WIKILINK_RE = re.compile(r"\[\[([A-Z][\w-]*(?:/[^\]\|]+)+?)(?:\|[^\]]*)?\]\]")
    for vf in (schema_p, os.path.join(root, "references", "vault-protocol.md"),
               os.path.join(root, "references", "people-context-protocol.md")):
        if not os.path.isfile(vf): continue
        rel_name = os.path.relpath(vf, root)
        for i, line in enumerate(open(vf, encoding="utf-8").read().split("\n"), 1):
            for link in WIKILINK_RE.findall(line):
                parts = link.split("/")
                top = parts[0]
                if top not in {a.split("/")[0] for a in AREAS}: continue
                if top in TOP_OF_MULTI and len(parts) >= 3:
                    # legal: {top}/{sub}/{key}/{file}; illegal: {top}/{key}/{sub}/{file}
                    if parts[1] not in SUBS_OF[top] and parts[2] in SUBS_OF[top]:
                        fail("vault-paths", f"{rel_name}:{i}: '[[{link}]]' puts the key above "
                                            f"'{parts[2]}' — the map says {top}/{parts[2]}/<key>/<file>")
                        continue
                if "archive" in parts[1:2]:
                    fail("vault-paths", f"{rel_name}:{i}: '[[{link}]]' uses an archive/ folder — "
                                        f"lifecycle status lives in frontmatter, not in a folder")

# -------------------------------------------------- 15. built-in subtypes
# The protocol's degraded path (registry unreachable) resolves a built-in by
# FILENAME: builtin://{artifact_type}/{subtype}-v1.md. All five ops-report
# built-ins declared subtype `ops-sprint-plan…` while the files were named
# `sprint-plan-v1.md`, so every one of them was unreachable in exactly the
# scenario the ladder exists for. The same files also carried literal markers
# citing template ids that were not their own.
MARKER_RE = re.compile(r"<!--\s*template:\s*([^\s>]+)(?:\s+version:\s*([^\s>]+))?\s*(@[^\s>]+)?\s*-->")
for tp in sorted(glob.glob(os.path.join(root, "templates", "built-in", "**", "*.md"), recursive=True)):
    rel_name = os.path.relpath(tp, root)
    txt = open(tp, encoding="utf-8").read()
    fm = fm_block(txt)
    def g(k):
        m0 = re.search(rf'^{k}:\s*"?([^"\n]+?)"?\s*$', fm, re.M)
        v = m0.group(1).strip() if m0 else None
        return None if v in (None, "", "null", "~") else v   # YAML null → absent
    tid, sub, ver = g("template_id"), g("subtype"), g("version")
    area = os.path.basename(os.path.dirname(tp))
    fname = os.path.basename(tp)
    if sub:
        expected = f"{sub}-v{(ver or '1').split('.')[0]}.md"
        if fname != expected:
            fail("builtin-subtypes", f"{rel_name}: subtype '{sub}' resolves to "
                                     f"builtin://{area}/{expected}, which is not this file — "
                                     f"the built-in ladder cannot reach it")
    if tid:
        expected_id = f"{area}-builtin-{sub or 'default'}"
        if tid != expected_id:
            warn("builtin-subtypes", f"{rel_name}: template_id '{tid}' breaks the "
                                     f"{{type}}-builtin-{{subtype}} convention (expected '{expected_id}')")
    m = MARKER_RE.search(txt)
    if m:
        if m.group(3) or not m.group(2):
            fail("builtin-subtypes", f"{rel_name}: marker '{m.group(0)}' — the one format is "
                                     f"`<!-- template: {{id}} version: {{ver}} -->` (template-protocol T-5)")
        elif tid and m.group(1) != tid:
            fail("builtin-subtypes", f"{rel_name}: marker cites '{m.group(1)}' but the file's "
                                     f"template_id is '{tid}'")

# ------------------------------------------------------- 12. artifact types
# Step T declares an artifact_type; template-protocol.md enumerates the legal set.
# roadmap / meeting-notes / focus / delegation-audit were declared by skills but
# absent from the enum, so template-library's wizard could not create them.
if not ARTIFACT_ENUM:
    warn("artifact-types", "template-protocol.md: could not locate the artifact_type enum block")
else:
    for sf in skill_files:
        folder = os.path.basename(os.path.dirname(sf))
        text = open(sf, encoding="utf-8").read()
        for m3 in re.finditer(r"`?artifact_type`?:\s*`?([a-z0-9-]+)`?", text):
            t = m3.group(1)
            if t in ("from", "the", "inferred"): continue
            if t not in ARTIFACT_ENUM:
                line = text[:m3.start()].count("\n") + 1
                fail("artifact-types", f"{folder}:{line}: artifact_type '{t}' is not in the template-protocol enum")

# ---------------------------------------------------- 13. chain contracts
# "← `X` (reason)" in A's chaining line asserts that X chains to A. If X never
# mentions A, the edge exists only on paper: experiment-tracker claimed inbounds
# from brainstorm-features and requirements-creator and was, in fact, unreachable.
# `←` carries two meanings: "X invokes me" (X must know about me) and "I pull
# from X by delegating to it" (X needn't know). The claim is satisfied by either.
INBOUND = re.compile(r"←\s*`([a-z][a-z0-9-]+)`")
skill_text = {os.path.basename(os.path.dirname(p)): open(p, encoding="utf-8").read()
              for p in skill_files}
reported = set()
for target, text in skill_text.items():
    lines = text.split("\n")
    body_without_chain_lines = "\n".join(l for l in lines if "←" not in l and "→" not in l)
    for line in lines:
        if "←" not in line: continue
        for source in set(INBOUND.findall(line)):
            if source not in SKILLS or source == target: continue
            if (target, source) in reported: continue
            x_knows_me = re.search(rf"\b{re.escape(target)}\b", skill_text[source])
            i_call_x = re.search(rf"\b{re.escape(source)}\b", body_without_chain_lines)
            if not x_knows_me and not i_call_x:
                reported.add((target, source))
                fail("chain-contracts",
                     f"{target}: claims '← {source}', but {source} never mentions {target} and "
                     f"{target} never calls {source} — wire the edge or drop the claim")

# -------------------------------------------------------------------- report
print(f"== Static lint: {root} ==")
print(f"skills: {len(skill_files)} | reference files: {len(ref_files)} | checks: {len(CHECKS.strip().splitlines())}")
print(f"\nFAIL: {len(fails)}")
for f in fails: print("  ✗", f)
print(f"\nWARN: {len(warns)}")
for w in warns: print("  •", w)
print("\nRESULT:", "GREEN ✅" if not fails else "RED ❌ (blockers present)")
sys.exit(1 if fails else 0)
