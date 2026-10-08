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
    ex0 = open(os.path.join(FIX, "existing-context.md"), encoding="utf-8").read()
    check("no extra blank lines introduced", t.count("\n\n\n") <= ex0.count("\n\n\n"), t.count("\n\n\n"))
    check("files only under _System in dry run", all(f.startswith(os.path.join("Core", "_System")) for f in files_under(out)), files_under(out))
else:
    check("merge keeps own team heading once", False, (rc, o))
shutil.rmtree(d)

# 2b — skip blocks the user declined, the Updated line, the head label
d, core, out = fresh()
open(os.path.join(core, "Core", "_System", "provider-manifest.yaml"), "a").write('head_label: "lead:"\n')
rc, o = run("--core", core, "--out", out, "--email", "a.one@zorg.example", "--dry-run", "--skip-blocks", "product,teams",
            "--existing-context", os.path.join(FIX, "existing-context.md"))
rep = report(o, "CONTEXT_REPORT") or {}
t2 = open(prop.replace(os.path.dirname(os.path.dirname(os.path.dirname(prop))), out), encoding="utf-8").read() if rc == 0 else ""
regp2 = open(os.path.join(out, "Core", "_System", "provider-registration.proposed.yaml"), encoding="utf-8").read() if rc == 0 else ""
check("skip blocks keeps declined blocks out", rc == 0 and "id=product" not in t2 and "id=teams" not in t2
      and "scope" in rep.get("added", []) and sorted(rep.get("skipped", [])) == ["product", "teams"]
      and "skip_blocks:" in regp2 and "  - product" in regp2, (rc, rep))
import datetime as _dt
check("updated line rewritten whole", ("Updated: %s (zorg-core refresh)." % _dt.date.today().isoformat()) in t2, t2[:300])
_tc = os.path.join(out, "Core", "_System", "team-context.md")
check("head label from manifest", os.path.isfile(_tc) and "— lead: Alex One" in open(_tc, encoding="utf-8").read(), "")
shutil.rmtree(d)

# 2c — a block id that is a prefix of another (team / teams) and the reference-section anchor
d, core, out = fresh()
rc, o = run("--core", core, "--out", out, "--email", "a.one@zorg.example", "--dry-run", "--skip-blocks", "scope,product",
            "--existing-context", os.path.join(FIX, "existing-context-teams.md"))
rep = report(o, "CONTEXT_REPORT") or {}
pp = os.path.join(out, "Core", "_System", "local-context.proposed.md")
t3 = open(pp, encoding="utf-8").read() if os.path.isfile(pp) else ""
check("a 'team' block never swallows 'teams'", rc == 0 and {"team", "teams"} <= set(rep.get("updated", []))
      and "teams" not in rep.get("added", []) and t3.count("<!-- zorg-core:begin id=teams ") == 1
      and t3.find("id=teams ") < t3.find("id=team ") and "zorg-core:section:begin" not in t3
      and "Teams map (old copy)" not in t3 and "### Teams map" in t3, (rc, rep))
shutil.rmtree(d)
d, core, out = fresh()
rc, o = run("--core", core, "--out", out, "--email", "a.one@zorg.example", "--dry-run",
            "--existing-context", os.path.join(FIX, "existing-context-teams.md"))
pp = os.path.join(out, "Core", "_System", "local-context.proposed.md")
t4 = open(pp, encoding="utf-8").read() if os.path.isfile(pp) else ""
sec, ons, cus = t4.find("zorg-core:section:begin"), t4.find("## Onboarding Status"), t4.find("## Custom Sections")
check("reference section goes before Custom Sections, not before Onboarding Status", rc == 0 and -1 < ons < sec < cus, (rc, ons, sec, cus))
shutil.rmtree(d)

# 2d — idempotent refresh, changelog with block versions, the "others" label
d, core, out = fresh()
open(os.path.join(core, "Core", "_System", "provider-manifest.yaml"), "a").write('jira_other_label: "also:"\n')
rc, o = run("--core", core, "--out", out, "--email", "a.one@zorg.example", "--dry-run",
            "--existing-context", os.path.join(FIX, "existing-context.md"))
p1 = os.path.join(out, "Core", "_System", "local-context.proposed.md")
P1 = open(p1, encoding="utf-8").read() if os.path.isfile(p1) else ""
check("changelog rows carry each block's own version", "| zorg-core `scope` | — | added (v0.4) |" in P1
      and "| zorg-core `team` | previous version | updated (v0.2) |" in P1, P1[-900:])
check("the 'others' label comes from the manifest", "(also: LEGACY)" in P1, "")
again = os.path.join(d, "again.md"); shutil.copy(p1, again)
out2 = os.path.join(d, "out2")
rc2, o2 = run("--core", core, "--out", out2, "--email", "a.one@zorg.example", "--dry-run", "--existing-context", again)
rep2 = report(o2, "CONTEXT_REPORT") or {}
p2 = os.path.join(out2, "Core", "_System", "local-context.proposed.md")
P2 = open(p2, encoding="utf-8").read() if os.path.isfile(p2) else "missing"
check("refresh twice is a no-op", rc2 == 0 and P2 == P1 and rep2.get("updated") == [] and rep2.get("added") == []
      and {"team", "scope", "teams"} <= set(rep2.get("unchanged", [])) and rep2.get("provider_entry") == "unchanged", (rc2, rep2))
shutil.rmtree(d)

# 2e — a vaults section closed by a horizontal rule: the provider entry goes inside it, before the rule
d, core, out = fresh()
src = open(os.path.join(FIX, "existing-context.md"), encoding="utf-8").read().replace("\n## Custom Sections", "\n---\n\n## Custom Sections")
hr = os.path.join(d, "hr-context.md"); open(hr, "w", encoding="utf-8").write(src)
rc, o = run("--core", core, "--out", out, "--email", "a.one@zorg.example", "--dry-run", "--existing-context", hr)
pp = os.path.join(out, "Core", "_System", "local-context.proposed.md")
t5 = open(pp, encoding="utf-8").read() if os.path.isfile(pp) else ""
check("provider entry sits inside the vaults section, before its rule", rc == 0
      and "| all | auto | never |\n\n### Vault Search MCP\n- zorg-core:" in t5 and "read-only\n\n---\n\n" in t5 and t5.find("### Vault Search MCP") < t5.find("zorg-core:section:begin")
      and t5.count("\n\n\n") <= src.count("\n\n\n"), t5[t5.find("## Obsidian"):t5.find("## Custom")+20])
shutil.rmtree(d)

# 2f — final-review regressions: error paths, role fallback, deny scope, exact team match, proposal dir
d, core, out = fresh()
mf = os.path.join(core, "Core", "_System", "provider-manifest.yaml")
good = open(mf, encoding="utf-8").read()
open(mf, "w", encoding="utf-8").write(good + "mcp2:\n  deep:\n    more: x\n")
rc, o = run("--core", core, "--out", out, "--email", "a.one@zorg.example", "--dry-run")
check("malformed manifest → exit 3 with file and line", rc == 3 and "provider-manifest.yaml" in o and "line" in o and "Traceback" not in o, (rc, o[-300:]))
open(mf, "w", encoding="utf-8").write(good.replace('  - "(^|/)_drafts/"', '  - "(unclosed"'))
rc, o = run("--core", core, "--out", out, "--email", "a.one@zorg.example", "--dry-run")
check("bad exclude regex → exit 3 naming the key", rc == 3 and "exclude" in o and "Traceback" not in o, (rc, o[-300:]))
open(mf, "w", encoding="utf-8").write(good)
bj = os.path.join(core, "Core", "_System", "access-bundles.json"); bgood = open(bj, encoding="utf-8").read()
open(bj, "w", encoding="utf-8").write(bgood[:-10])
rc, o = run("--core", core, "--out", out, "--email", "a.one@zorg.example", "--dry-run")
check("broken role model → exit 3 naming the file", rc == 3 and "access-bundles.json" in o and "Traceback" not in o, (rc, o[-300:]))
open(bj, "w", encoding="utf-8").write(bgood)
rc, o = run("--core", core, "--out", out, "--email", "c.three@zorg.example", "--dry-run")
check("an inferred role missing from the model falls back with a notice", rc == 0 and "role pm" in o and "engineer" in o, (rc, o[:300]))
rc, o = run("--core", core, "--out", out, "--email", "c.three@zorg.example", "--role", "marketer", "--dry-run")
check("an explicit role missing from the model still stops", rc == 3 and "marketer" in o, (rc, o[-200:]))
own = os.path.join(d, "own-deny.md")
open(own, "w", encoding="utf-8").write(open(os.path.join(FIX, "existing-context.md"), encoding="utf-8").read().replace("_none_", "my note OWNER-PRIVATE"))
rc, o = run("--core", core, "--out", out, "--email", "a.one@zorg.example", "--dry-run", "--existing-context", own)
check("deny patterns never block on the user's own text", rc == 0, (rc, o[-200:]))
tc = os.path.join(out, "Core", "_System", "team-context.md")
check("team membership is an exact match (team-alpha-two is not alpha)", os.path.isfile(tc) and "Dee Four" not in open(tc, encoding="utf-8").read() and "Bea Two" in open(tc, encoding="utf-8").read(), "")
shutil.rmtree(d)
d, core, out = fresh()
priv = os.path.join(d, "private-proposals")
rc, o = run("--core", core, "--out", core, "--email", "a.one@zorg.example", "--in-place", "--dry-run",
            "--existing-context", os.path.join(FIX, "existing-context.md"), "--proposal-dir", priv)
check("--proposal-dir keeps the proposal out of the core", rc == 0 and os.path.isfile(os.path.join(priv, "local-context.proposed.md"))
      and not os.path.exists(os.path.join(core, "Core", "_System", "local-context.proposed.md"))
      and not os.path.exists(os.path.join(core, "Core", "_System", "context-merge-report.md")), (rc, o[-200:]))
shutil.copy(os.path.join(FIX, "existing-context.md"), os.path.join(priv, "local-context.existing.md"))
rc, o = run("--core", core, "--out", core, "--email", "a.one@zorg.example", "--in-place", "--dry-run", "--proposal-dir", priv)
r = report(o, "CONTEXT_REPORT") or {}
check("a context copy in the proposal folder is picked up without a flag", rc == 0 and r.get("mode") == "merge"
      and str(r.get("existing_context", "")).startswith(priv), (rc, r.get("mode"), r.get("existing_context")))
shutil.rmtree(d)
d, core, out = fresh()
bf = os.path.join(core, "Core", "_System", "context-blocks.md")
src = open(bf, encoding="utf-8").read()
open(bf, "w", encoding="utf-8").write(src.replace("Zorg App only.", "Zorg App only. OWNER-PRIVATE"))
rc, o = run("--core", core, "--out", out, "--email", "a.one@zorg.example", "--dry-run", "--existing-context", os.path.join(FIX, "existing-context.md"))
check("a deny hit names the provider block", rc == 4 and "scope" in o, (rc, o[-200:]))
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
