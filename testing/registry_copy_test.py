#!/usr/bin/env python3
"""TC-registry-copy — testing/registry_copy.py.

A registry syncs the plugin from `.ai-registry/skills/<name>/`, never the root, and needs
three manifests with one name there. The copy is built from the index: unstaged work never
reaches it, the maintainer's own folders stay out, a Cursor manifest is derived, a symlink
is refused. Built on a throw-away git repository holding a fictional plugin; stdlib + git
only. Run from the repo root.
"""
import json, os, shutil, subprocess, sys, tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT = os.path.join(ROOT, "testing", "registry_copy.py")
fails = 0
def check(name, cond, detail=""):
    global fails
    fails += not cond
    print(("✅" if cond else "❌"), name, ("" if cond else "-> " + str(detail)[:400]))

def git(cwd, *a):
    return subprocess.run(["git", *a], cwd=cwd, capture_output=True, text=True,
                          env=dict(os.environ, GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@example.com",
                                   GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@example.com"))

def write(d, rel, text, exe=False):
    full = os.path.join(d, rel)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    open(full, "w").write(text)
    os.chmod(full, 0o755 if exe else 0o644)

def manifest(name="demo", version="1.0.0"):
    return json.dumps({"name": name, "version": version, "description": "A demo plugin.",
                       "author": {"name": "Demo"}}, indent=2) + "\n"

with tempfile.TemporaryDirectory() as d:
    git(d, "init", "-q", "-b", "main")
    os.makedirs(os.path.join(d, "testing"))
    shutil.copy(SCRIPT, os.path.join(d, "testing", "registry_copy.py"))
    write(d, ".claude-plugin/plugin.json", manifest())
    market = lambda source: json.dumps({"name": "demo-market", "plugins": [{"name": "demo", "source": source}]}) + "\n"
    write(d, ".claude-plugin/marketplace.json", market("./.ai-registry/skills/demo"))
    write(d, ".codex-plugin/plugin.json", manifest())
    write(d, "skills/hello/SKILL.md", "---\nname: hello\n---\n# Hello\n")
    write(d, "scripts/run.sh", "#!/bin/sh\necho hi\n", exe=True)
    write(d, "docs/notes.md", "design notes\n")
    write(d, ".github/workflows/ci.yml", "on: push\n")
    write(d, "README.md", "# Demo\n")
    git(d, "add", "."); git(d, "commit", "-q", "-m", "init")
    copy = os.path.join(d, ".ai-registry", "skills", "demo")
    def run(*args):
        p = subprocess.run([sys.executable, os.path.join("testing", "registry_copy.py"), *args], cwd=d,
                           capture_output=True, text=True)
        return p.returncode, p.stdout + p.stderr

    rc, out = run()
    check("build writes the copy under the manifest's name", rc == 0 and os.path.isfile(os.path.join(copy, "skills/hello/SKILL.md")), out)
    have = {os.path.relpath(os.path.join(dp, f), copy) for dp, _, fs in os.walk(copy) for f in fs}
    check("maintainer folders and the marketplace catalogue stay out",
          not any(p.startswith(("testing/", "docs/", ".github/")) for p in have)
          and ".claude-plugin/marketplace.json" not in have, sorted(have))
    cur = json.load(open(os.path.join(copy, ".cursor-plugin/plugin.json")))
    check("a Cursor manifest is derived from plugin.json",
          cur.get("name") == "demo" and cur.get("version") == "1.0.0" and cur.get("skills") == "./skills/", cur)
    check("the executable bit survives", os.access(os.path.join(copy, "scripts/run.sh"), os.X_OK))
    rc, out = run("--check")
    check("--check passes right after a build", rc == 0, out)
    rc, out = run("--manifests")
    check("--manifests passes while the versions match", rc == 0, out)
    # Since v4.1.1: a host that imports the whole repository refuses a tree with a second
    # plugin manifest, so the marketplace entry must install from the copy, never from "./".
    write(d, ".claude-plugin/marketplace.json", market("./"))
    rc, out = run("--manifests")
    check("--manifests fails while the marketplace installs from the root, and names the copy",
          rc == 1 and 'source "./"' in out and "./.ai-registry/skills/demo" in out, out)
    write(d, ".claude-plugin/marketplace.json", '{"name": "demo-market", "plugins": []}\n')
    rc, out = run("--manifests")
    check("--manifests fails when the marketplace has no entry for the plugin", rc == 1 and "no entry named 'demo'" in out, out)
    write(d, ".claude-plugin/marketplace.json", market("./.ai-registry/skills/demo"))

    write(d, "skills/hello/SKILL.md", "---\nname: hello\n---\n# Hello, work in progress\n")
    run()
    check("an unstaged edit never reaches the copy",
          "work in progress" not in open(os.path.join(copy, "skills/hello/SKILL.md")).read())
    git(d, "checkout", "-q", "--", "skills/hello/SKILL.md")

    write(d, "skills/hello/references/new.md", "a file the release adds\n")
    git(d, "add", "skills/hello/references/new.md")
    rc, out = run("--check")
    check("--check fails on a staged file the copy lacks, and names it",
          rc == 1 and "missing: skills/hello/references/new.md" in out, out)
    run()
    check("a staged new file reaches the copy", os.path.isfile(os.path.join(copy, "skills/hello/references/new.md")))

    write(d, ".claude-plugin/plugin.json", manifest(version="1.1.0"))
    rc, out = run("--manifests")
    check("--manifests fails once plugin.json moves on without a rebuild", rc == 1 and "1.1.0" in out, out)

    os.symlink("README.md", os.path.join(d, "skills", "hello", "link.md"))
    git(d, "add", "skills/hello/link.md")
    rc, out = run()
    check("a staged symlink is refused with one line, not a traceback",
          rc == 2 and "symlink" in out and "Traceback" not in out, out)
    git(d, "rm", "-q", "--cached", "skills/hello/link.md"); os.remove(os.path.join(d, "skills", "hello", "link.md"))

    git(d, "rm", "-q", "--cached", ".codex-plugin/plugin.json")
    rc, out = run()
    check("no Codex manifest staged → refused, a registry would reject the copy", rc == 2 and "codex" in out.lower(), out)

print("RESULT:", "GREEN ✅" if not fails else "RED ❌", "(%d failed)" % fails)
sys.exit(1 if fails else 0)
