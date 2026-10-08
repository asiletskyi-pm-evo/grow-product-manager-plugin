#!/usr/bin/env python3
"""TC-ctx-3100-bundle — scripts/provider_bundle.py on the fictional Zorg core
(testing/fixtures/context-connect/). The builder copies a role-filtered bundle of
a shared-context provider's core, proposes the provider's context blocks for the
user's local-context.md, and writes the user's overlay notes — every name, folder
and template from the provider manifest (references/context-provider-protocol.md §3a, §9).

Stdlib only; run from the repo root. Each case works on a temp copy of the fixture.
"""
import json, os, re, shutil, subprocess, sys, tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIX = os.path.join(ROOT, "testing", "fixtures", "context-connect")
SCRIPT = os.path.join(ROOT, "scripts", "provider_bundle.py")

def run(*args):
    p = subprocess.run([sys.executable, SCRIPT] + list(args), capture_output=True, text=True, timeout=60)
    return p.returncode, p.stdout + p.stderr

def report(out, tag):
    for line in out.splitlines():
        if line.startswith(tag + " "):
            return json.loads(line[len(tag) + 1:])
    return None

def files_under(d):
    return sorted(os.path.relpath(os.path.join(dp, f), d) for dp, _, fn in os.walk(d) for f in fn)

fails = 0
def check(name, cond, detail=""):
    global fails
    fails += not cond
    print(("✅" if cond else "❌"), name, ("" if cond else "-> " + str(detail)[:600]))

def fresh():
    d = tempfile.mkdtemp()
    core = os.path.join(d, "core"); shutil.copytree(os.path.join(FIX, "zorg-core"), core)
    return d, core, os.path.join(d, "out")

# 1
d, core, out = fresh()
rc, o = run("--core", core, "--out", out, "--email", "a.one@zorg.example", "--dry-run")
check("dry run resolves team and role", rc == 0 and "team alpha" in o and "role pm" in o, (rc, o))
check("dry run writes nothing without a context", not os.path.exists(out) or files_under(out) == [], files_under(out) if os.path.exists(out) else "")
shutil.rmtree(d)

# 2
d, core, out = fresh()
rc, o = run("--core", core, "--out", out, "--email", "a.one@zorg.example", "--dry-run",
            "--existing-context", os.path.join(FIX, "existing-context.md"))
prop = os.path.join(out, "Core", "_System", "local-context.proposed.md")
rep = report(o, "CONTEXT_REPORT") or {}
if rc == 0 and os.path.isfile(prop):
    t = open(prop, encoding="utf-8").read()
    plain = re.sub(r"<!--\s*([a-z][a-z0-9:-]*):begin.*?<!--\s*\1:end[^>]*-->", "", t, flags=re.S)
    check("merge keeps own team heading once", plain.count("### Team: Alpha (A)") == 1 and "stale copy" not in t
          and t.count("<!-- zorg-core:begin id=team ") == 1 and "team" in rep.get("updated", []), (rep, plain[:400]))
    check("reference-only and added blocks", "product" in rep.get("reference_only", []) and
          {"scope", "teams"} <= set(rep.get("added", [])) and rep.get("discrepancies") == [], rep)
    check("provider bullet proposed", re.search(r"^### Vault Search MCP\n(?:.*\n)*?- zorg-core: ", t, re.M) is not None, t[-800:])
    check("files only under _System in dry run", all(f.startswith(os.path.join("Core", "_System")) for f in files_under(out)), files_under(out))
else:
    check("merge keeps own team heading once", False, (rc, o))
shutil.rmtree(d)

# 3
d, core, out = fresh()
rc, o = run("--core", core, "--out", out, "--email", "a.one@zorg.example", "--dry-run",
            "--existing-context", os.path.join(FIX, "nested-context.md"))
check("nested markers abort", rc == 4 and not os.path.exists(os.path.join(out, "Core", "_System", "local-context.proposed.md")), (rc, o))
shutil.rmtree(d)

# 4
d, core, out = fresh()
bf = os.path.join(core, "Core", "_System", "context-blocks.md")
src = open(bf, encoding="utf-8").read()
open(bf, "w", encoding="utf-8").write(src.replace("Zorg App only.", "Zorg App only. OWNER-PRIVATE"))
rc, o = run("--core", core, "--out", out, "--email", "a.one@zorg.example", "--dry-run",
            "--existing-context", os.path.join(FIX, "existing-context.md"))
check("deny pattern aborts", rc == 4 and "deny" in o.lower(), (rc, o))
shutil.rmtree(d)

# 5
d, core, out = fresh()
rc, o = run("--core", core, "--out", out, "--email", "nobody@zorg.example", "--dry-run")
check("unknown email", rc == 2 and "UNKNOWN_TEAM" in o, (rc, o))
shutil.rmtree(d)

# 6
d, core, out = fresh()
rc, o = run("--core", core, "--out", out, "--email", "a.one@zorg.example",
            "--existing-context", os.path.join(FIX, "existing-context.md"), "--jira-write", "own")
res = report(o, "BUNDLE_RESULT") or {}
def rd(*p):
    f = os.path.join(out, *p)
    return open(f, encoding="utf-8").read() if os.path.isfile(f) else ""
person = rd("Core", "People", "a-one.md"); mission = rd("Core", "Products", "Zorg App", "Missions", "Mission One.md")
dash = rd("Core", "Dashboard.md"); man = rd("Core", "_System", "bundle-manifest.md"); now = rd("Core", "Now.md")
regp = rd("Core", "_System", "provider-registration.proposed.yaml")
check("write mode copies the role bundle", rc == 0 and os.path.isfile(os.path.join(out, "Core", "Teams", "team-alpha.md"))
      and os.path.isfile(os.path.join(out, "Wiki", "SPACE", "Pages", "Alpha page.md"))
      and not os.path.exists(os.path.join(out, "Core", "_drafts", "draft.md"))
      and not os.path.exists(os.path.join(out, "Core", "People", "c-three.md")), (rc, o))
check("people cards keep registry fields only", "Alex leads Alpha." in person and "## Notes" not in person
      and "meetings_count" not in person, person)
check("personal-layer links delinked", "Core/Meetings/" not in mission and "personal layer" in mission and "sync notes" in mission, mission)
check("dashboard rewritten and pruned", "my focus" in dash and "Missing note" not in dash and "Core/Meetings/" not in dash
      and "[[Core/Teams/_index|Teams]]" in dash, dash)
check("bundle manifest frontmatter", 'team: "team-alpha"' in man and "role_profile: pm" in man and 'core_version: "0.2"' in man, man)
check("focus note from default template", "Mission One" in now and "Alex One" in now, now)
check("registration proposed", "id: zorg-core" in regp and "schema: provider-registration/1" in regp and out in regp
      and "jira_write: own" in regp, regp)
check("bundle result line", res.get("team") == "alpha" and res.get("role") == "pm" and res.get("files", 0) >= 7, res)
check("team block carries the write scope", "own project" in rd("Core", "_System", "team-context.md").lower(), rd("Core", "_System", "team-context.md"))
shutil.rmtree(d)

# 7
d, core, out = fresh()
tdir = os.path.join(core, "Core", "_System", "provider-templates"); os.makedirs(tdir)
open(os.path.join(tdir, "now.md"), "w").write("# FOCUS-TEMPLATE {{NAME}}\nteam {{TEAM_SLUG}}\n")
mf = os.path.join(core, "Core", "_System", "provider-manifest.yaml")
open(mf, "a").write("templates_dir: Core/_System/provider-templates\n")
rc, o = run("--core", core, "--out", out, "--email", "a.one@zorg.example")
check("templates from manifest", rc == 0 and "FOCUS-TEMPLATE Alex One" in open(os.path.join(out, "Core", "Now.md"), encoding="utf-8").read()
      if os.path.isfile(os.path.join(out, "Core", "Now.md")) else False, (rc, o))
shutil.rmtree(d)

# 8
d, core, out = fresh()
rc, o = run("--core", core, "--out", core, "--email", "b.two@zorg.example", "--in-place", "--no-personal-overlay")
check("in-place analyst run copies nothing and writes no overlay", rc == 0 and "role analyst" in o
      and not os.path.exists(os.path.join(core, "Core", "Now.md"))
      and os.path.isfile(os.path.join(core, "Core", "_System", "bundle-manifest.md")), (rc, o))
shutil.rmtree(d)

# 9
tok_file = os.path.join(ROOT, "testing", "org-tokens.local")
toks = [l.strip() for l in open(tok_file, encoding="utf-8")] if os.path.isfile(tok_file) else []
toks = [t for t in toks if t and not t.startswith("#")]
if toks:
    rx = re.compile("|".join((r"\b" if t[:1].isalnum() else "") + re.escape(t) + (r"\b" if t[-1:].isalnum() else "") for t in toks), re.I)
    texts = [SCRIPT] + [os.path.join(ROOT, "scripts", "provider_templates", f) for f in os.listdir(os.path.join(ROOT, "scripts", "provider_templates"))] \
        if os.path.isdir(os.path.join(ROOT, "scripts", "provider_templates")) else [SCRIPT]
    hits = [(os.path.basename(p), m.group(0)) for p in texts if os.path.isfile(p) for m in [rx.search(open(p, encoding="utf-8").read())] if m]
    check("no org identifiers in the builder or its templates", not hits, hits)
else:
    print("ℹ️  no org identifiers check skipped — testing/org-tokens.local absent")

print("RESULT:", "GREEN ✅" if not fails else "RED ❌", "(%d failed)" % fails)
sys.exit(1 if fails else 0)
