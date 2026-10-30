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
rc, o = run("--core", core, "--out", out, "--email", "a.one@zorg.example", "--propose-only")
check("propose-only resolves team and role", rc == 0 and "team alpha" in o and "role pm" in o, (rc, o))
check("propose-only writes nothing without a context", not os.path.exists(out) or files_under(out) == [], files_under(out) if os.path.exists(out) else "")
shutil.rmtree(d)

# 2
d, core, out = fresh()
rc, o = run("--core", core, "--out", out, "--email", "a.one@zorg.example", "--propose-only",
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
    check("files only under _System when proposing", all(f.startswith(os.path.join("Core", "_System")) for f in files_under(out)), files_under(out))
else:
    check("merge keeps own team heading once", False, (rc, o))
shutil.rmtree(d)

# 2b — skip blocks the user declined, the Updated line, the head label
d, core, out = fresh()
open(os.path.join(core, "Core", "_System", "provider-manifest.yaml"), "a").write('head_label: "lead:"\n')
rc, o = run("--core", core, "--out", out, "--email", "a.one@zorg.example", "--propose-only", "--skip-blocks", "product,teams",
            "--existing-context", os.path.join(FIX, "existing-context.md"))
rep = report(o, "CONTEXT_REPORT") or {}
t2 = open(prop.replace(os.path.dirname(os.path.dirname(os.path.dirname(prop))), out), encoding="utf-8").read() if rc == 0 else ""
regp2 = open(os.path.join(out, "Core", "_System", "provider-registration.proposed.yaml"), encoding="utf-8").read() if rc == 0 else ""
check("skip blocks keeps declined blocks out", rc == 0 and "id=product" not in t2 and "id=teams" not in t2
      and "scope" in rep.get("added", []) and sorted(rep.get("skipped", [])) == ["product", "teams"]
      and "skip_blocks:" in regp2 and "  - product" in regp2, (rc, rep))
import datetime as _dt
check("updated line without a note gets the date and the refresh item", ("Updated: %s (zorg-core refresh)." % _dt.date.today().isoformat()) in t2, t2[:300])
_tc = os.path.join(out, "Core", "_System", "team-context.md")
check("head label from manifest", os.path.isfile(_tc) and "— lead: Alex One" in open(_tc, encoding="utf-8").read(), "")
shutil.rmtree(d)

# 2c — a block id that is a prefix of another (team / teams) and the reference-section anchor
d, core, out = fresh()
rc, o = run("--core", core, "--out", out, "--email", "a.one@zorg.example", "--propose-only", "--skip-blocks", "scope,product",
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
rc, o = run("--core", core, "--out", out, "--email", "a.one@zorg.example", "--propose-only",
            "--existing-context", os.path.join(FIX, "existing-context-teams.md"))
pp = os.path.join(out, "Core", "_System", "local-context.proposed.md")
t4 = open(pp, encoding="utf-8").read() if os.path.isfile(pp) else ""
sec, ons, cus = t4.find("zorg-core:section:begin"), t4.find("## Onboarding Status"), t4.find("## Custom Sections")
check("reference section goes before Custom Sections, not before Onboarding Status", rc == 0 and -1 < ons < sec < cus, (rc, ons, sec, cus))
shutil.rmtree(d)

# 2d — idempotent refresh, changelog with block versions, the "others" label
d, core, out = fresh()
open(os.path.join(core, "Core", "_System", "provider-manifest.yaml"), "a").write('jira_other_label: "also:"\n')
rc, o = run("--core", core, "--out", out, "--email", "a.one@zorg.example", "--propose-only",
            "--existing-context", os.path.join(FIX, "existing-context.md"))
p1 = os.path.join(out, "Core", "_System", "local-context.proposed.md")
P1 = open(p1, encoding="utf-8").read() if os.path.isfile(p1) else ""
check("changelog rows carry each block's own version", "| zorg-core `scope` | — | added (v0.4) |" in P1
      and "| zorg-core `team` | previous version | updated (v0.2) |" in P1, P1[-900:])
check("the 'others' label comes from the manifest", "(also: LEGACY)" in P1, "")
again = os.path.join(d, "again.md"); shutil.copy(p1, again)
out2 = os.path.join(d, "out2")
rc2, o2 = run("--core", core, "--out", out2, "--email", "a.one@zorg.example", "--propose-only", "--existing-context", again)
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
rc, o = run("--core", core, "--out", out, "--email", "a.one@zorg.example", "--propose-only", "--existing-context", hr)
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
rc, o = run("--core", core, "--out", out, "--email", "a.one@zorg.example", "--propose-only")
check("malformed manifest → exit 3 with file and line", rc == 3 and "provider-manifest.yaml" in o and "line" in o and "Traceback" not in o, (rc, o[-300:]))
open(mf, "w", encoding="utf-8").write(good.replace('  - "(^|/)_drafts/"', '  - "(unclosed"'))
rc, o = run("--core", core, "--out", out, "--email", "a.one@zorg.example", "--propose-only")
check("bad exclude regex → exit 3 naming the key", rc == 3 and "exclude" in o and "Traceback" not in o, (rc, o[-300:]))
open(mf, "w", encoding="utf-8").write(good)
bj = os.path.join(core, "Core", "_System", "access-bundles.json"); bgood = open(bj, encoding="utf-8").read()
open(bj, "w", encoding="utf-8").write(bgood[:-10])
rc, o = run("--core", core, "--out", out, "--email", "a.one@zorg.example", "--propose-only")
check("broken role model → exit 3 naming the file", rc == 3 and "access-bundles.json" in o and "Traceback" not in o, (rc, o[-300:]))
open(bj, "w", encoding="utf-8").write(bgood)
rc, o = run("--core", core, "--out", out, "--email", "c.three@zorg.example", "--propose-only")
check("an inferred role missing from the model falls back with a notice", rc == 0 and "role pm" in o and "engineer" in o, (rc, o[:300]))
rc, o = run("--core", core, "--out", out, "--email", "c.three@zorg.example", "--role", "marketer", "--propose-only")
check("an explicit role missing from the model still stops", rc == 3 and "marketer" in o, (rc, o[-200:]))
own = os.path.join(d, "own-deny.md")
open(own, "w", encoding="utf-8").write(open(os.path.join(FIX, "existing-context.md"), encoding="utf-8").read().replace("_none_", "my note OWNER-PRIVATE"))
rc, o = run("--core", core, "--out", out, "--email", "a.one@zorg.example", "--propose-only", "--existing-context", own)
check("deny patterns never block on the user's own text", rc == 0, (rc, o[-200:]))
tc = os.path.join(out, "Core", "_System", "team-context.md")
check("team membership is an exact match (team-alpha-two is not alpha)", os.path.isfile(tc) and "Dee Four" not in open(tc, encoding="utf-8").read() and "Bea Two" in open(tc, encoding="utf-8").read(), "")
shutil.rmtree(d)
d, core, out = fresh()
priv = os.path.join(d, "private-proposals")
rc, o = run("--core", core, "--out", core, "--email", "a.one@zorg.example", "--in-place", "--propose-only",
            "--existing-context", os.path.join(FIX, "existing-context.md"), "--proposal-dir", priv)
check("--proposal-dir keeps the proposal out of the core", rc == 0 and os.path.isfile(os.path.join(priv, "local-context.proposed.md"))
      and not os.path.exists(os.path.join(core, "Core", "_System", "local-context.proposed.md"))
      and not os.path.exists(os.path.join(core, "Core", "_System", "context-merge-report.md")), (rc, o[-200:]))
shutil.copy(os.path.join(FIX, "existing-context.md"), os.path.join(priv, "local-context.existing.md"))
rc, o = run("--core", core, "--out", core, "--email", "a.one@zorg.example", "--in-place", "--propose-only", "--proposal-dir", priv)
r = report(o, "CONTEXT_REPORT") or {}
check("a context copy in the proposal folder is picked up without a flag", rc == 0 and r.get("mode") == "merge"
      and str(r.get("existing_context", "")).startswith(priv), (rc, r.get("mode"), r.get("existing_context")))
shutil.rmtree(d)
d, core, out = fresh()
bf = os.path.join(core, "Core", "_System", "context-blocks.md")
src = open(bf, encoding="utf-8").read()
open(bf, "w", encoding="utf-8").write(src.replace("Zorg App only.", "Zorg App only. OWNER-PRIVATE"))
rc, o = run("--core", core, "--out", out, "--email", "a.one@zorg.example", "--propose-only", "--existing-context", os.path.join(FIX, "existing-context.md"))
check("a deny hit names the provider block", rc == 4 and "scope" in o, (rc, o[-200:]))
shutil.rmtree(d)

# 3
d, core, out = fresh()
rc, o = run("--core", core, "--out", out, "--email", "a.one@zorg.example", "--propose-only",
            "--existing-context", os.path.join(FIX, "nested-context.md"))
check("nested markers abort", rc == 4 and not os.path.exists(os.path.join(out, "Core", "_System", "local-context.proposed.md")), (rc, o))
shutil.rmtree(d)

# 4
d, core, out = fresh()
bf = os.path.join(core, "Core", "_System", "context-blocks.md")
src = open(bf, encoding="utf-8").read()
open(bf, "w", encoding="utf-8").write(src.replace("Zorg App only.", "Zorg App only. OWNER-PRIVATE"))
rc, o = run("--core", core, "--out", out, "--email", "a.one@zorg.example", "--propose-only",
            "--existing-context", os.path.join(FIX, "existing-context.md"))
check("deny pattern aborts", rc == 4 and "deny" in o.lower(), (rc, o))
shutil.rmtree(d)

# 5
d, core, out = fresh()
rc, o = run("--core", core, "--out", out, "--email", "nobody@zorg.example", "--propose-only")
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
check("registration proposed", "id: zorg-core" in regp and "schema: provider-registration/2" in regp and out in regp
      and "jira_write: own" in regp, regp)
check("registration v2 proposed", "schema: provider-registration/2" in regp and "core_root: " in regp
      and "namespace: zorg-core" in regp and "blocks_file: Core/_System/context-blocks.md" in regp and "rank: 1000" in regp, regp)
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

# 2g — v3.10.1: a refresh keeps the user's own note on the Updated line
_today = _dt.date.today().isoformat()
def updated_after(line):
    d, core, out = fresh()
    src = open(os.path.join(FIX, "existing-context.md"), encoding="utf-8").read().replace(
        "> Generated: 2026-04-15. Updated: 2026-09-29.", line)
    ex = os.path.join(d, "note-context.md"); open(ex, "w", encoding="utf-8").write(src)
    rc, o = run("--core", core, "--out", out, "--email", "a.one@zorg.example", "--propose-only", "--existing-context", ex)
    pp = os.path.join(out, "Core", "_System", "local-context.proposed.md")
    t = open(pp, encoding="utf-8").read() if os.path.isfile(pp) else ""
    shutil.rmtree(d)
    m = re.search(r"^> Generated:.*$", t, re.M)
    return rc, (m.group(0) if m else (rc, o[-300:]))
rc, got = updated_after("> Generated: 2026-04-15. Updated: 2026-09-29 (zorg-core refresh; brain: daily sync (local)).")
check("refresh keeps the user's note on the Updated line",
      got == "> Generated: 2026-04-15. Updated: %s (zorg-core refresh; brain: daily sync (local))." % _today, got)
rc, got = updated_after("> Generated: 2026-04-15. Updated: 2026-09-29 (other-core refresh; my note).")
check("an older refresh of another provider leaves the Updated line",
      got == "> Generated: 2026-04-15. Updated: %s (zorg-core refresh; my note)." % _today, got)
rc, got = updated_after("> Generated: 2026-04-15. Updated: %s (other-core refresh; my note)." % _today)
check("a same-day refresh of another provider stays on the Updated line",
      got == "> Generated: 2026-04-15. Updated: %s (zorg-core refresh; other-core refresh; my note)." % _today, got)

# 2h — v3.10.1: registration paths, an orphan marker, a title with separators, the --propose-only name
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import ctx_common as cc
d, core, _ = fresh()
out = os.path.join(d, "out #1")
rc, o = run("--core", core, "--out", out, "--email", "a.one@zorg.example", "--propose-only",
            "--existing-context", os.path.join(FIX, "existing-context.md"))
regp = os.path.join(out, "Core", "_System", "provider-registration.proposed.yaml")
reg = cc.read_yaml_subset(open(regp, encoding="utf-8").read()) if os.path.isfile(regp) else {}
check("registration paths survive a ' #' in a folder name", reg.get("paths") == [os.path.abspath(out)], (rc, reg.get("paths")))
shutil.rmtree(d)

d, core, out = fresh()
orphan = os.path.join(d, "orphan-context.md")
open(orphan, "w", encoding="utf-8").write(open(os.path.join(FIX, "existing-context.md"), encoding="utf-8").read().rstrip("\n")
                                         + "\n\n<!-- zorg-core:begin id=orphan v=0.1 -->\nleft open\n")
rc, o = run("--core", core, "--out", out, "--email", "a.one@zorg.example", "--propose-only", "--existing-context", orphan)
check("an orphan begin marker stops the proposal", rc == 4
      and not os.path.exists(os.path.join(out, "Core", "_System", "local-context.proposed.md")), (rc, o[-300:]))
shutil.rmtree(d)

d, core, out = fresh()
open(os.path.join(core, "Core", "_System", "provider-manifest.yaml"), "a").write('title: "Zorg core, shared; v2"\n')
rc, o = run("--core", core, "--out", out, "--email", "a.one@zorg.example", "--propose-only",
            "--existing-context", os.path.join(FIX, "existing-context.md"))
pp = os.path.join(out, "Core", "_System", "local-context.proposed.md")
bl = [x for x in cc.vault_search_bullets(open(pp, encoding="utf-8").read()) if x["id"] == "zorg-core"] if os.path.isfile(pp) else []
check("a provider title with ',' and ';' reads back whole", bl != [] and "Zorg core, shared; v2" in bl[0]["scope"]
      and bl[0]["mode"] == "snapshot" and bl[0]["read_only"], (rc, bl))
shutil.rmtree(d)

d, core, out = fresh()
rc, o = run("--core", core, "--out", out, "--email", "a.one@zorg.example", "--propose-only")
check("--propose-only resolves team and role and writes nothing without a context", rc == 0 and "team alpha" in o
      and (not os.path.exists(out) or files_under(out) == []), (rc, o[-300:]))
rc, o = run("--core", core, "--out", out, "--email", "a.one@zorg.example", "--dry-run")
check("--dry-run still works and names its new spelling", rc == 0 and "--propose-only" in o, (rc, o[-300:]))
shutil.rmtree(d)

# 10 — v3.13.0: the registration proposal is provider-registration/2 (what `ctx provider plan/apply` read)
import ctx_repos as cr

def read_root(*parts):
    return open(os.path.join(ROOT, *parts), encoding="utf-8").read()

def proposed_registration(manifest_extra="", manifest_edit=None, vault=None, existing=None):
    """(parsed registration, core, out, exit code, output) of a --propose-only run on a fresh copy of the Zorg core."""
    d, core, out = fresh()
    mf = os.path.join(core, "Core", "_System", "provider-manifest.yaml")
    text = open(mf, encoding="utf-8").read()
    if manifest_edit:
        text = text.replace(*manifest_edit)
    open(mf, "w", encoding="utf-8").write(text + manifest_extra)
    ctx = existing or os.path.join(FIX, "existing-context.md")
    if vault is not None:
        ctx = os.path.join(d, "vault-context.md")
        open(ctx, "w", encoding="utf-8").write(open(os.path.join(FIX, "existing-context.md"), encoding="utf-8").read().replace(
            "/Users/name/Vault", vault.replace("{d}", d).replace("{core}", core)))
    rc, o = run("--core", core, "--out", out, "--email", "a.one@zorg.example", "--propose-only", "--existing-context", ctx)
    path = os.path.join(out, "Core", "_System", "provider-registration.proposed.yaml")
    reg = cc.read_yaml_subset(open(path, encoding="utf-8").read()) if os.path.isfile(path) else {}
    return reg, d, core, out, rc, o

reg, d, core, out, rc, o = proposed_registration()
check("v2 registration, as the reader reads it: schema, identity, rank as a number, core_root, namespace, blocks_file, no products",
      rc == 0 and reg.get("schema") == "provider-registration/2" and reg.get("id") == "zorg-core" and reg.get("kind") == "bundle"
      and reg.get("authority") == "org" and reg.get("rank") == 1000 and type(reg.get("rank")) is int
      and reg.get("core_root") == os.path.abspath(core) and reg.get("namespace") == "zorg-core"
      and reg.get("blocks_file") == "Core/_System/context-blocks.md" and reg.get("products") == [], (rc, reg))
check("…the v1 keys are all still there: paths, writable, team, role, jira_write, status, mode, access",
      reg.get("paths") == [os.path.abspath(out)] and reg.get("writable") == ["Core/Now.md", "Core/TODO*", "Core/_personal/"]
      and reg.get("team") == "team-alpha" and reg.get("role") == "pm" and reg.get("jira_write") == "ask"
      and reg.get("status") == "active" and reg.get("mode") == "snapshot" and reg.get("access") == "local"
      and reg.get("skip_blocks") == [] and reg.get("index") == "" and reg.get("stale_after_days") == 30, reg)
check("a manifest that names no server gives no endpoint", "endpoint" not in reg, reg)
rep = cr.normalise(reg)
check("the repository reader takes it whole: an explicit namespace, the core folder, the blocks file, the rank",
      rep["namespace_explicit"] is True and rep["namespace"] == "zorg-core" and rep["core_root"] == os.path.abspath(core)
      and rep["blocks_file"] == "Core/_System/context-blocks.md" and rep["rank"] == 1000 and rep["products"] == []
      and rep["endpoint"] == {"url": "", "root": "", "headers_env": ""}, rep)
fch = cr.fetch(rep)
check("…and a fetch through it finds the core's blocks in the folder, with no warning to add a namespace",
      fch["source"] == "folder" and fch["namespace"] == "zorg-core" and set(fch["blocks"]) == {"scope", "product", "teams"}
      and cr.namespace_warning(rep) is None, fch)
shutil.rmtree(d)

SERVER = 'mcp:\n  url: https://context.zorg.example/mcp\n  transport: mcp-remote --transport http-only\n  access: vpn\n'
reg, d, core, out, rc, o = proposed_registration(manifest_extra=SERVER)
check("the manifest names a server: endpoint.url from mcp.url, access from mcp.access, no root outside a vault",
      rc == 0 and reg.get("endpoint") == {"url": "https://context.zorg.example/mcp"} and reg.get("access") == "vpn"
      and cr.normalise(reg)["endpoint"] == {"url": "https://context.zorg.example/mcp", "root": "", "headers_env": ""}, reg)
shutil.rmtree(d)

reg, d, core, out, rc, o = proposed_registration(manifest_extra=SERVER, vault="{d}")
check("a core nested in a vault of the user's context: endpoint.root is the core's folder in that vault, with the slash",
      rc == 0 and reg.get("endpoint") == {"url": "https://context.zorg.example/mcp", "root": "core/"}, (rc, reg.get("endpoint"), o[-200:]))
shutil.rmtree(d)

reg, d, core, out, rc, o = proposed_registration(manifest_extra=SERVER, vault="{core}")
check("a core that is itself the vault is not nested: no root", rc == 0 and reg.get("endpoint") == {"url": "https://context.zorg.example/mcp"},
      (rc, reg.get("endpoint")))
shutil.rmtree(d)

reg, d, core, out, rc, o = proposed_registration(manifest_extra=SERVER, vault="{d}/elsewhere")
check("a core outside every vault of the context (a sibling folder with a name that starts the same) has no root",
      rc == 0 and reg.get("endpoint") == {"url": "https://context.zorg.example/mcp"}, (rc, reg.get("endpoint")))
shutil.rmtree(d)

reg, d, core, out, rc, o = proposed_registration(manifest_extra='mcp:\n  url: "https://context.zorg.example/mcp?v=1#main"\n')
check("a server address with '#' and '?' survives the registration", reg.get("endpoint") == {"url": "https://context.zorg.example/mcp?v=1#main"}, reg)
shutil.rmtree(d)

for authority, rank in (("team", 500), ("personal", 100), ("weird", 500)):
    reg, d, core, out, rc, o = proposed_registration(manifest_edit=("authority: org", "authority: %s" % authority))
    check("rank follows the authority (%s → %d)" % (authority, rank), rc == 0 and reg.get("rank") == rank and reg.get("authority") == authority, (rc, reg))
    shutil.rmtree(d)

reg, d, core, out, rc, o = proposed_registration(manifest_edit=("namespace: zorg-core", "namespace: zorg-blocks"))
check("a namespace of its own in the manifest is the registration's", rc == 0 and reg.get("namespace") == "zorg-blocks" and reg.get("id") == "zorg-core", (rc, reg))
shutil.rmtree(d)

reg, d, core, out, rc, o = proposed_registration(manifest_edit=("blocks_file: Core/_System/context-blocks.md\n", ""))
check("a manifest with no blocks file: the registration names none", rc == 0 and "blocks_file" not in reg and reg.get("namespace") == "zorg-core", (rc, reg))
shutil.rmtree(d)

reg, d, core, out, rc, o = proposed_registration(manifest_edit=("namespace: zorg-core\n", ""))
check("a manifest with no namespace: the registration names the id, as the builder does", rc == 0 and reg.get("namespace") == "zorg-core", (rc, reg))
shutil.rmtree(d)

# the section a new context gets, and the connect procedure the skill points to
check("section template says edits are kept", "kept" in read_root("scripts", "provider_templates", "context-section.md"),
      read_root("scripts", "provider_templates", "context-section.md"))
steps = read_root("skills", "context-connect", "references", "connect-steps.md")
skill = read_root("skills", "context-connect", "SKILL.md")
check("connect-steps uses plan and apply", "ctx.py\" provider plan" in steps and "provider apply" in steps and "provider adopt --apply" in steps, "")
check("connect-steps: the answers are --choose and --add, an unreachable repository (exit 5) writes nothing, the old path stays for no store",
      "--choose" in steps and "--add" in steps and "exit 5" in steps and "unreachable" in steps and "provider_bundle.py" in steps, "")
check("the skill is 0.5.0 and a refresh with a store never stamps Updated or appends a changelog",
      "version: 0.8.1" in skill and "Updated:" in skill and "Changelog" in skill, skill[:200])

# 11 — fix round 1: a refresh keeps a registration the user completed; a removed block recommends keeping the text; the apply carve-out
# (the builder only proposes the registration — it never writes the file in the user's vault, so the rule lives in the procedure)
flat = lambda s: re.sub(r"\s+", " ", s)
steps_f, skill_f = flat(steps), flat(skill)
reg61 = steps_f[steps_f.index("## §6 Register and finish"):steps_f.index("## §7")]
step61 = skill_f[skill_f.index("## Step 6"):skill_f.index("## What is forbidden")]
for label, text in (("connect-steps §6.1", reg61), ("SKILL.md Step 6.1", step61)):
    check("%s: an existing registration is kept — a refresh updates synced_at and source_version, adds a missing v2 key, never changes a present one"
          % label, "synced_at" in text and "source_version" in text and "never chang" in text and "headers_env" in text
          and "products" in text and "blocks_source" in text and "home_record" in text and "paused" in text, text[:500])
    check("%s: replacing it by the proposal needs the user's explicit yes after the differences are shown" % label,
          "explicit" in text and "differences" in text, text[:500])
check("a v1 registration gets only the two dates until the user says yes (no silent upgrade)",
      "v1" in reg61 and "only the two dates" in reg61, reg61[:600])
refresh_q = steps_f[steps_f.index("Ask **once**"):steps_f.index("3. Apply the answers")]
check("a `?` row whose block the core still offers recommends theirs; a block the core removed (`?` or `⚠`) recommends mine",
      "`?` with the block still offered → theirs" in refresh_q and "removed" in refresh_q and "mine" in refresh_q
      and "`?` → theirs." not in refresh_q and "recommended: mine" in refresh_q, refresh_q[:700])
step4 = skill_f[skill_f.index("## Step 4"):skill_f.index("## Step 5")]
check("SKILL.md Step 4 repeats the split: `?` theirs, mine when the core removed the block",
      "`?` theirs" in step4 and "mine when the core removed the block" in step4, step4[:900])
forbid = skill_f[skill_f.index("## What is forbidden"):skill_f.index("## Quality Standards")]
check("the 'never overwrite local-context.md without a yes' rule has the snapshot-backed apply carve-out",
      "without an explicit" in forbid and "ctx provider apply" in forbid and "snapshot" in forbid and "ctx undo" in forbid
      and "`~`" in forbid and "`−`" in forbid and "one message" in forbid, forbid)
check("connect-steps says the same where it says there is no question: the plan was shown, the snapshot is the gate",
      "No `⚠`, `+` or `?` row → no question" in steps_f and "snapshot" in steps_f[steps_f.index("No `⚠`, `+` or `?` row"):][:400]
      and "one message" in steps_f[steps_f.index("No `⚠`, `+` or `?` row"):][:400], steps_f[steps_f.index("No `⚠`"):][:400])

# 12 — the docs pass (Task 12): the residual wording of the re-review of Task 11
core_keys = ["`core_root`", "`namespace`", "`blocks_file`", "`paths`", "`endpoint.url`", "`endpoint.root`", "`rank`"]
for label, text in (("connect-steps §6.1", reg61), ("SKILL.md Step 6.1", step61)):
    check("%s: a kept core-derived key that differs from the proposal is reported in one line and the replacement is offered on a yes; exit 5 points to it"
          % label, all(k in text for k in core_keys) and "one line" in text and "replacement" in text and "yes" in text and "exit 5" in text,
          [k for k in core_keys if k not in text])
    said = ["`products: []`", "`status: active`", "as defaults"] if label.startswith("connect-steps") else ["carries a default for the others"]
    check("%s: the proposal lacks some user-finished keys and carries defaults for others — no 'never carries' for products or status" % label,
          all(s in text for s in said) and "never carries" not in text and "always says" not in text, (said, text[:700]))
check("connect-steps §6.1 and SKILL.md Step 6.1: a nested v2 key that is missing counts as missing",
      "A nested key counts" in reg61 and "a nested one too" in step61, (reg61[:300], step61[:300]))
check("connect-steps §6.1: a v2 file with no namespace gets it from the manifest, silently; §4a says the same, and a v1 file asks",
      "no `namespace` gets it from the manifest the same way, silently" in reg61
      and "A v2 file that lacks only the key gets it from the manifest on the Refresh, silently" in steps_f
      and "A v1 file is the user's until they say yes" in steps_f, "")
check("the carve-out names local-context.md only: the focus note, the to-do note and the rest keep the yes",
      "names `local-context.md` only" in forbid and "the focus note, the to-do note and everything else keep the \"yes\"" in forbid, forbid)
check("the order is the plan in one line → apply → the report, and ~ and − are never asked in either case (SKILL.md Step 4 and connect-steps §4a)",
      "the plan in one line → `apply` → the report" in step4 and "never asked, in either case" in step4
      and "the plan in one line → `apply` → the report" in steps_f and "whether or not there is a question about other rows" in steps_f,
      (step4[-500:], refresh_q[-500:]))
check("exit 5 in connect-steps: the core moved → point to the kept-key line and offer the replacement on a yes",
      "point to that line and offer the replacement on a yes" in steps_f, "")
check("connect-steps: the blocks the report lists as reference_only show as + in the next plan; exit 4 also means a refused run",
      "reference_only" in steps_f and "show as `+` in the next plan" in steps_f and "a store inside a provider's folder, a busy lock" in steps_f, "")

# 10 — v3.14.0 Task 9: no module-wide reader; a caller passes its own to every function that reads the core
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import provider_bundle as pb  # noqa: E402
check("provider_bundle has no module variable READ (a caller in a helper thread must never swap it for another)",
      not hasattr(pb, "READ"), "")
CORE_DIR = os.path.join(FIX, "zorg-core")
m_plain, _ = pb.read_manifest(CORE_DIR)
seen = []
def tracing(p):
    seen.append(os.path.relpath(p, ROOT))
    with open(p, encoding="utf-8") as f:
        return f.read()
m_traced, _ = pb.read_manifest(CORE_DIR, read=tracing)
check("read_manifest(…, read=) reads through the reader it is given", m_traced == m_plain
      and seen == [os.path.relpath(os.path.join(CORE_DIR, "Core", "_System", "provider-manifest.yaml"), ROOT)], seen)
J = json.load(open(os.path.join(CORE_DIR, "Core", "_System", "access-bundles.json"), encoding="utf-8"))
plain = pb.team_context(CORE_DIR, m_plain, "alpha", J["teams"]["alpha"], J, "own")
seen[:] = []
traced = pb.team_context(CORE_DIR, m_plain, "alpha", J["teams"]["alpha"], J, "own", read=tracing)
people = sorted(os.path.relpath(os.path.join(CORE_DIR, "Core", "People", n), ROOT)
                for n in os.listdir(os.path.join(CORE_DIR, "Core", "People")) if n.endswith(".md") and not n.startswith("_"))
check("team_context(…, read=) gives the same block and reads the card, every people card and the template through the reader",
      traced[0] == plain[0] and os.path.relpath(os.path.join(CORE_DIR, "Core", "Teams", "team-alpha.md"), ROOT) in seen
      and sorted(p for p in seen if os.sep + "People" + os.sep in p) == people
      and any(p.endswith("team-block.md") for p in seen), seen)
check("…and with no reader it reads the files itself, as the bundle builder always has (rd with no reader)",
      pb.rd(os.path.join(CORE_DIR, "Core", "Teams", "team-alpha.md")) == open(os.path.join(CORE_DIR, "Core", "Teams", "team-alpha.md"),
                                                                                 encoding="utf-8").read(), "")

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

# tools_file (v4.2.0, tool-registry.md §5): the team's tools list goes into every bundle with the manifest; a path
# that leaves the core is never copied.
d, core, out = fresh()
with open(os.path.join(core, "Core", "_System", "provider-manifest.yaml"), "a", encoding="utf-8") as f:
    f.write("tools_file: Core/_System/tools.yaml\n")
with open(os.path.join(core, "Core", "_System", "tools.yaml"), "w", encoding="utf-8") as f:
    f.write('tools:\n  - name: "Zorg Board"\n    kind: "mcp"\n')
rc, o = run("--core", core, "--out", out, "--email", "a.one@zorg.example", "--jira-write", "own")
check("tools_file copied into the bundle with the manifest", rc == 0 and
      os.path.isfile(os.path.join(out, "Core", "_System", "tools.yaml")), (rc, o[-400:]))
out_b = os.path.join(d, "out-b")
rc, o = run("--core", core, "--out", out_b, "--email", "c.three@zorg.example", "--role", "analyst", "--jira-write", "none")
check("tools_file copied for another team and role too", rc == 0 and
      os.path.isfile(os.path.join(out_b, "Core", "_System", "tools.yaml")), (rc, o[-400:]))
with open(os.path.join(d, "outside.yaml"), "w", encoding="utf-8") as f:
    f.write('tools:\n  - name: "Outside"\n')
mp = os.path.join(core, "Core", "_System", "provider-manifest.yaml")
with open(mp, encoding="utf-8") as f:
    mt = f.read()
with open(mp, "w", encoding="utf-8") as f:
    f.write(mt.replace("tools_file: Core/_System/tools.yaml", "tools_file: ../outside.yaml"))
out_c = os.path.join(d, "out-c")
rc, o = run("--core", core, "--out", out_c, "--email", "a.one@zorg.example", "--jira-write", "own")
check("a tools_file outside the core is never copied", rc == 0 and
      not [f for f in files_under(d) if f.endswith("outside.yaml") and f != "outside.yaml"], files_under(d))
shutil.rmtree(d)

print("RESULT:", "GREEN ✅" if not fails else "RED ❌", "(%d failed)" % fails)
sys.exit(1 if fails else 0)
